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
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.utils.formatter import format_analysis_from_template
import pandas as pd

# --- Basic Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
SYMBOL, TERM, TIMEFRAME = range(3)

# --- Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends or edits the main menu message."""
    config = get_config()
    ui_cfg = config['ui']
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = ui_cfg['MESSAGES']['start'].format(now=now)

    keyboard = [
        [InlineKeyboardButton(ui_cfg['BUTTONS']['analyze'], callback_data=ui_cfg['CALLBACK_DATA']['analyze_start'])],
        [InlineKeyboardButton(ui_cfg['BUTTONS']['status'], callback_data=ui_cfg['CALLBACK_DATA']['bot_status'])],
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

    config = get_config()
    ui_cfg = config['ui']

    keyboard = [[InlineKeyboardButton(ui_cfg['BUTTONS']['back_to_main'], callback_data=ui_cfg['CALLBACK_DATA']['main_menu'])]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=ui_cfg['MESSAGES']['bot_status'],
        reply_markup=reply_markup
    )

# --- Analysis Conversation ---
async def analyze_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the analysis conversation. Asks for a symbol."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    ui_cfg = config['ui']
    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    cb_data = ui_cfg['CALLBACK_DATA']

    keyboard = [
        [InlineKeyboardButton(symbol, callback_data=f"{cb_data['symbol_prefix']}{symbol}") for symbol in watchlist[i:i+2]]
        for i in range(0, len(watchlist), 2)
    ]
    keyboard.append([InlineKeyboardButton(ui_cfg['BUTTONS']['back'], callback_data=cb_data['main_menu'])])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=ui_cfg['MESSAGES']['select_symbol'],
        reply_markup=reply_markup
    )
    return SYMBOL

async def select_term(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the analysis term (long, medium, short)."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    symbol = query.data.split(cb_data['symbol_prefix'], 1)[1]
    context.user_data['symbol'] = symbol

    keyboard = [
        [
            InlineKeyboardButton(ui_cfg['BUTTONS']['long_term'], callback_data=cb_data['term_long']),
            InlineKeyboardButton(ui_cfg['BUTTONS']['medium_term'], callback_data=cb_data['term_medium']),
            InlineKeyboardButton(ui_cfg['BUTTONS']['short_term'], callback_data=cb_data['term_short']),
        ],
        [InlineKeyboardButton(ui_cfg['BUTTONS']['back'], callback_data=cb_data['analyze_start'])],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=ui_cfg['MESSAGES']['symbol_selected'].format(symbol=symbol),
        reply_markup=reply_markup
    )
    return TERM

async def select_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the specific timeframe (e.g., 1H, 4H)."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    term_key = query.data.split(cb_data['term_prefix'], 1)[1]
    context.user_data['term'] = term_key

    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
    timeframes = timeframe_groups.get(term_key, [])

    if not timeframes:
        await query.edit_message_text(text=ui_cfg['MESSAGES']['config_error'])
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f"{cb_data['timeframe_prefix']}{tf}") for tf in timeframes[i:i+3]]
        for i in range(0, len(timeframes), 3)
    ]
    # Go back to the term selection
    keyboard.append([InlineKeyboardButton(ui_cfg['BUTTONS']['back'], callback_data=f"{cb_data['symbol_prefix']}{context.user_data['symbol']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # We need a user-friendly term name, we can get it from the button text in the previous step
    # This is a bit of a workaround. A better solution might be to store a display name in the config.
    term_display_name = term_key.replace('_', ' ')


    await query.edit_message_text(
        text=ui_cfg['MESSAGES']['select_term'].format(term=term_display_name),
        reply_markup=reply_markup
    )
    return TIMEFRAME

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs the analysis and sends the formatted result."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    timeframe = query.data.split(cb_data['timeframe_prefix'], 1)[1]
    context.user_data['timeframe'] = timeframe
    symbol = context.user_data['symbol']

    await query.edit_message_text(text=ui_cfg['MESSAGES']['analysis_inprogress'].format(symbol=symbol, timeframe=timeframe))

    try:
        fetcher = DataFetcher(config)
        analyzer = FiboAnalyzer(config, fetcher)
        limit = 1000  # Reasonable limit for fast responses

        await query.edit_message_text(text=ui_cfg['MESSAGES']['fetching_data'].format(symbol=symbol, timeframe=timeframe))

        data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=limit)
        if not data_dict or 'data' not in data_dict or not data_dict['data']:
            await query.message.reply_text(ui_cfg['MESSAGES']['data_fetch_error'])
            await start(update, context)
            return ConversationHandler.END

        df = pd.DataFrame(data_dict['data'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)

        analysis_info = analyzer.get_analysis(df, symbol, timeframe)
        formatted_report = format_analysis_from_template(analysis_info, symbol, timeframe)

        await query.message.reply_text(formatted_report, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"An error occurred during analysis for {symbol} on {timeframe}: {e}", exc_info=True)
        await query.message.reply_text(ui_cfg['MESSAGES']['analysis_error'])

    await start(update, context)
    return ConversationHandler.END

# --- Periodic & Error Handlers ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

async def run_periodic_analysis(application: Application):
    """Runs analysis periodically and sends formatted alerts."""
    config = get_config()
    fetcher = DataFetcher(config)
    analyzer = FiboAnalyzer(config, fetcher)
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')

    if not admin_chat_id:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID not set. Periodic alerts will be skipped.")
        return

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])
    logger.info(f"--- Starting Periodic Analysis for {len(watchlist)} symbols ---")

    for symbol in watchlist:
        for timeframe in timeframes:
            try:
                data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=300)
                if not data_dict or 'data' not in data_dict or not data_dict['data']:
                    continue

                df = pd.DataFrame(data_dict['data'])
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df.dropna(inplace=True)

                analysis_info = analyzer.get_analysis(df, symbol, timeframe)
                if analysis_info.get('signal') in ['BUY', 'SELL']:
                    report = format_analysis_from_template(analysis_info, symbol, timeframe)
                    await application.bot.send_message(chat_id=admin_chat_id, text=report, parse_mode='Markdown')
                    logger.info(f"Sent '{analysis_info['signal']}' alert for {symbol} on {timeframe} to admin.")
            except Exception as e:
                logger.error(f"Error in periodic analysis for {symbol} on {timeframe}: {e}")
            await asyncio.sleep(2)
    logger.info("--- Periodic Analysis Complete ---")

async def post_init(application: Application) -> None:
    """Initializes the background scheduler."""
    config = get_config()
    interval = config.get('trading', {}).get('ANALYSIS_INTERVAL_MINUTES', 15)
    scheduler = AsyncIOScheduler(timezone="UTC")
    # The scheduler is configured but disabled by default.
    # To enable, uncomment the following two lines.
    # Be aware of API rate limits and server load before enabling.
    # scheduler.add_job(run_periodic_analysis, 'interval', minutes=interval, args=[application])
    # scheduler.start()
    logger.info(f"Scheduler is configured but DISABLED. Automatic analysis will not run.")

# --- Conversation Handler Definition ---
def setup_conversation_handler(config):
    """Creates the ConversationHandler using settings from the config."""
    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    return ConversationHandler(
        entry_points=[CallbackQueryHandler(analyze_entry, pattern=f"^{cb_data['analyze_start']}$")],
        states={
            SYMBOL: [CallbackQueryHandler(select_term, pattern=f"^{cb_data['symbol_prefix']}")],
            TERM: [CallbackQueryHandler(select_timeframe, pattern=f"^{cb_data['term_prefix']}")],
            TIMEFRAME: [
                CallbackQueryHandler(run_analysis, pattern=f"^{cb_data['timeframe_prefix']}"),
                # Allows returning to the term selection from the timeframe selection
                CallbackQueryHandler(select_term, pattern=f"^{cb_data['symbol_prefix']}")
            ],
        },
        fallbacks=[CallbackQueryHandler(start, pattern=f"^{cb_data['main_menu']}$")],
        per_message=False
    )


def main() -> None:
    """Start the bot."""
    config = get_config()
    token = config.get('telegram', {}).get('TOKEN')
    if not token:
        logger.error("Telegram BOT_TOKEN not found in .env file.")
        return

    application = Application.builder().token(token).post_init(post_init).build()

    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    # Setup handlers
    conv_handler = setup_conversation_handler(config)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern=f"^{cb_data['main_menu']}$"))
    application.add_handler(CallbackQueryHandler(bot_status, pattern=f"^{cb_data['bot_status']}$"))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
