import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher
from src.data_retrieval.exceptions import APIError, NetworkError
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.strategies.exceptions import InsufficientDataError
from src.utils.formatter import format_analysis_from_template
from src.localization import get_text
from src.realtime.websocket_client import OKXWebSocketClient
from src.realtime.monitoring_manager import monitoring_manager
import pandas as pd

# --- Basic Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
SYMBOL, TERM, TIMEFRAME, MONITOR_DECISION = range(4)

# --- Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends or edits the main menu message."""
    now = datetime.now()
    text = (
        get_text("start_header") +
        f"{get_text('bot_status_ok')}\n"
        f"__{now.strftime('%Y-%m-%d %H:%M:%S')}__"
    )

    keyboard = [
        [InlineKeyboardButton(get_text("button_analyze"), callback_data='analyze_start')],
        [InlineKeyboardButton(get_text("button_bot_status"), callback_data='bot_status')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the bot status and provides a back button."""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(get_text("button_back_to_main"), callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_text("bot_status_periodic_disabled"),
        reply_markup=reply_markup
    )

# --- Analysis Conversation ---
async def analyze_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the analysis conversation. Asks for a symbol."""
    query = update.callback_query
    await query.answer()

    config = context.bot_data['config']
    watchlist = config.get('trading', {}).get('WATCHLIST', [])

    keyboard = [
        [InlineKeyboardButton(symbol, callback_data=f'symbol_{symbol}') for symbol in watchlist[i:i+2]]
        for i in range(0, len(watchlist), 2)
    ]
    keyboard.append([InlineKeyboardButton(get_text("button_back"), callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_text("ask_symbol"),
        reply_markup=reply_markup
    )
    return SYMBOL

async def select_term(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the analysis term (long, medium, short)."""
    query = update.callback_query
    await query.answer()

    context.user_data['symbol'] = query.data.split('_', 1)[1]

    keyboard = [
        [
            InlineKeyboardButton(get_text("button_long_term"), callback_data='term_long_term'),
            InlineKeyboardButton(get_text("button_medium_term"), callback_data='term_medium_term'),
            InlineKeyboardButton(get_text("button_short_term"), callback_data='term_short_term'),
        ],
        [InlineKeyboardButton(get_text("button_back"), callback_data='analyze_start')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_text("ask_term").format(symbol=context.user_data['symbol']),
        reply_markup=reply_markup
    )
    return TERM

async def select_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the specific timeframe (e.g., 1H, 4H)."""
    query = update.callback_query
    await query.answer()

    term_key = query.data.split('_', 1)[1]
    context.user_data['term'] = term_key

    config = context.bot_data['config']
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
    timeframes = timeframe_groups.get(term_key, [])

    if not timeframes:
        await query.edit_message_text(text=get_text("error_config_timeframes"))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f'timeframe_{tf}') for tf in timeframes[i:i+3]]
        for i in range(0, len(timeframes), 3)
    ]
    keyboard.append([InlineKeyboardButton(get_text("button_back"), callback_data=f'symbol_{context.user_data["symbol"]}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_text("ask_timeframe").format(term=term_key.replace('_', ' ')),
        reply_markup=reply_markup
    )
    return TIMEFRAME

async def _fetch_and_prepare_data(fetcher: DataFetcher, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Fetches historical data and prepares it as a pandas DataFrame.
    Raises exceptions on failure.
    """
    data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=limit)

    df = pd.DataFrame(data_dict['data'])
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Ensure essential candle data is present before sending to the analyzer.
    # This prevents errors from corrupted data fetched from the exchange.
    df.dropna(subset=['timestamp', 'open', 'high', 'low', 'close', 'volume'], inplace=True)

    return df

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs the analysis and sends the formatted result."""
    query = update.callback_query
    await query.answer()

    context.user_data['timeframe'] = query.data.split('_', 1)[1]
    symbol = context.user_data['symbol']
    timeframe = context.user_data['timeframe']
    config = context.bot_data['config']
    fetcher = DataFetcher(config)
    analyzer = FiboAnalyzer(config, fetcher)

    try:
        await query.edit_message_text(text=get_text("fetching_data").format(symbol=symbol, timeframe=timeframe))

        df = await _fetch_and_prepare_data(fetcher, symbol, timeframe, limit=1500)

        await query.edit_message_text(text=get_text("analysis_running").format(symbol=symbol, timeframe=timeframe))
        analysis_info = analyzer.get_analysis(df, symbol, timeframe)
        formatted_report = format_analysis_from_template(analysis_info, symbol, timeframe)

        await query.message.reply_text(formatted_report, parse_mode='Markdown')

    except InsufficientDataError:
        logger.warning(f"Caught InsufficientDataError for {symbol} on {timeframe}.")
        await query.message.reply_text(
            get_text("error_not_enough_historical_data").format(symbol=symbol, timeframe=timeframe)
        )
    except NetworkError as e:
        logger.error(f"Network error for {symbol} on {timeframe}: {e}")
        await query.message.reply_text(get_text("error_api_connection"))
    except APIError as e:
        logger.error(f"API error for {symbol} on {timeframe}: {e}")
        if e.status_code == '51001':
            await query.message.reply_text(get_text("error_invalid_symbol").format(symbol=symbol))
        else:
            await query.message.reply_text(get_text("error_unknown_api").format(status_code=e.status_code))
    except Exception as e:
        logger.error(f"An unexpected error occurred during analysis for {symbol} on {timeframe}: {e}", exc_info=True)
        await query.message.reply_text(get_text("error_generic"))
        # End conversation on error
        await start(update, context)
        return ConversationHandler.END

    # --- If analysis is successful, ask the user what to do next ---
    context.user_data['last_analysis'] = analysis_info

    keyboard = [
        [
            InlineKeyboardButton(get_text("button_monitor_follow"), callback_data=f'monitor_follow_{symbol}'),
            InlineKeyboardButton(get_text("button_monitor_ignore"), callback_data='monitor_ignore')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use reply_text on the original message to add a new message with buttons
    await query.message.reply_text(
        text=get_text("ask_what_to_do"),
        reply_markup=reply_markup
    )

    return MONITOR_DECISION

# --- Periodic & Error Handlers ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

async def run_periodic_analysis(application: Application):
    """Runs analysis periodically and sends formatted alerts."""
    config = application.bot_data['config']
    fetcher = DataFetcher(config)
    analyzer = FiboAnalyzer(config, fetcher)
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')

    if not admin_chat_id:
        logger.warning(get_text("warning_no_admin_id"))
        return

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])
    logger.info(get_text("periodic_start_log").format(count=len(watchlist)))

    for symbol in watchlist:
        for timeframe in timeframes:
            try:
                df = await _fetch_and_prepare_data(fetcher, symbol, timeframe, limit=300)
                analysis_info = analyzer.get_analysis(df, symbol, timeframe)

                if analysis_info.get('signal') in ['BUY', 'SELL']:
                    report = format_analysis_from_template(analysis_info, symbol, timeframe)
                    await application.bot.send_message(chat_id=admin_chat_id, text=report, parse_mode='Markdown')
                    logger.info(get_text("periodic_sent_alert_log").format(
                        signal=analysis_info['signal'], symbol=symbol, timeframe=timeframe
                    ))
            except (APIError, NetworkError) as e:
                 logger.error(f"Error in periodic analysis for {symbol} on {timeframe}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in periodic analysis for {symbol} on {timeframe}: {e}")
            await asyncio.sleep(2)
    logger.info(get_text("periodic_end_log"))

async def post_init(application: Application) -> None:
    """Initializes background tasks like the scheduler and WebSocket client."""
    config = application.bot_data.get('config', get_config())
    application.bot_data['config'] = config

    # --- Define the WebSocket message handler inside post_init to access 'application' ---
    async def on_ws_message(message: dict):
        """
        This function is called by the WebSocket client for each new ticker message.
        It checks the price against any monitored levels.
        """
        symbol = message.get('instId')
        price_str = message.get('last')
        if not symbol or not price_str:
            return

        try:
            price = float(price_str)
            alerts_to_send = monitoring_manager.check_price(symbol, price)

            for alert in alerts_to_send:
                level_name = alert.get('level_name', 'N/A').replace('_', ' ').title()
                alert_text = get_text("alert_level_hit").format(
                    symbol=alert['symbol'],
                    level_name=level_name,
                    level_price=alert['level_price'],
                    current_price=alert['current_price']
                )
                await application.bot.send_message(
                    chat_id=alert['chat_id'],
                    text=alert_text,
                    parse_mode='Markdown'
                )
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing WebSocket message: {e} | Message: {message}")

    # --- Initialize Periodic Analysis Scheduler (as before) ---
    interval = config.get('trading', {}).get('ANALYSIS_INTERVAL_MINUTES', 15)
    scheduler = AsyncIOScheduler(timezone="UTC")
    logger.info(get_text("scheduler_disabled_log"))

    # --- Initialize and run WebSocket Client in the background ---
    exchange_config = config.get('exchange', {})
    api_key = exchange_config.get('API_KEY')
    api_secret = exchange_config.get('API_SECRET')
    passphrase = exchange_config.get('PASSWORD')
    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    sandbox_mode = exchange_config.get('SANDBOX_MODE', True)

    if api_key and api_secret and passphrase:
        logger.info("API credentials found, starting WebSocket client...")
        ws_client = OKXWebSocketClient(
            api_key, api_secret, passphrase,
            watchlist,
            on_message_callback=on_ws_message,
            sandbox_mode=sandbox_mode
        )
        # Run the websocket listener as a background task
        asyncio.create_task(ws_client.listen())
    else:
        logger.warning("WebSocket client not started: Missing API Key, Secret, or Passphrase.")

# --- Monitoring Decision Handlers ---
async def handle_follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Follow' button press. Adds the analysis to the monitoring manager."""
    query = update.callback_query
    await query.answer()

    symbol = query.data.split('_', 2)[2]
    analysis_data = context.user_data.get('last_analysis')
    chat_id = query.message.chat_id

    if not analysis_data:
        await query.edit_message_text(text=get_text("error_generic"))
        return ConversationHandler.END

    monitoring_manager.add_monitoring(symbol, analysis_data, chat_id)

    await query.edit_message_text(
        text=get_text("monitoring_started").format(symbol=symbol)
    )

    # We don't call start() here, just end the conversation.
    # The user can start a new action from the main menu when ready.
    return ConversationHandler.END

async def handle_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Ignore' button press."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text=get_text("monitoring_ignored"))

    return ConversationHandler.END


# --- Conversation Handler Definition ---
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(analyze_entry, pattern='^analyze_start$')],
    states={
        SYMBOL: [CallbackQueryHandler(select_term, pattern='^symbol_')],
        TERM: [CallbackQueryHandler(select_timeframe, pattern='^term_')],
        TIMEFRAME: [
            CallbackQueryHandler(run_analysis, pattern='^timeframe_'),
            CallbackQueryHandler(select_term, pattern='^symbol_')
        ],
        MONITOR_DECISION: [
            CallbackQueryHandler(handle_follow, pattern='^monitor_follow_'),
            CallbackQueryHandler(handle_ignore, pattern='^monitor_ignore$')
        ]
    },
    fallbacks=[CallbackQueryHandler(start, pattern='^main_menu$')],
    per_message=False
)


def main() -> None:
    """Start the bot."""
    config = get_config()
    token = config.get('telegram', {}).get('TOKEN')
    if not token:
        logger.error(get_text("error_no_token"))
        return

    application = Application.builder().token(token).post_init(post_init).build()

    # Store the config in bot_data for easy access
    application.bot_data['config'] = config

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(bot_status, pattern='^bot_status$'))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    logger.info(get_text("bot_starting_log"))
    application.run_polling()

if __name__ == '__main__':
    main()