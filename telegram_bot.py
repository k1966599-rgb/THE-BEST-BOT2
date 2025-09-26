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

from functools import wraps
from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.utils.formatter import format_analysis_from_template
from src.utils.exceptions import DataUnavailableError, AnalysisError
from src.utils.state_manager import StateManager
from src.utils.config_validator import validate_config
from pydantic import ValidationError
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

# --- Admin Features ---
def admin_only(func):
    """Decorator to restrict usage of a command to the admin."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # We get the config from bot_data to ensure it's the reloaded version.
        admin_chat_id = context.bot_data.get('config', {}).get('telegram', {}).get('ADMIN_CHAT_ID')
        if not admin_chat_id:
            logger.error("ADMIN_CHAT_ID is not configured. Cannot verify admin user.")
            return

        user_id = update.effective_user.id
        if str(user_id) != str(admin_chat_id):
            await update.message.reply_text("عذرًا، هذا الأمر مخصص للمشرف فقط.")
            logger.warning(f"Unauthorized access attempt to admin command by user {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@admin_only
async def add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a symbol to the watchlist."""
    try:
        symbol = context.args[0].upper()
        state_manager: StateManager = context.bot_data['state_manager']

        watchlist = state_manager.get_watchlist()
        if symbol in watchlist:
            await update.message.reply_text(f"العملة {symbol} موجودة بالفعل في قائمة المراقبة.")
            return

        watchlist.append(symbol)
        state_manager.update_watchlist(watchlist)
        await update.message.reply_text(f"✅ تم إضافة {symbol} إلى قائمة المراقبة.\nالقائمة الحالية: {', '.join(watchlist)}")
        logger.info(f"Admin {update.effective_user.id} added {symbol} to the watchlist.")

    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /add SYMBOL-USDT")

@admin_only
async def remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a symbol from the watchlist."""
    try:
        symbol_to_remove = context.args[0].upper()
        state_manager: StateManager = context.bot_data['state_manager']

        watchlist = state_manager.get_watchlist()
        if symbol_to_remove not in watchlist:
            await update.message.reply_text(f"العملة {symbol_to_remove} غير موجودة في قائمة المراقبة.")
            return

        watchlist.remove(symbol_to_remove)
        state_manager.update_watchlist(watchlist)
        await update.message.reply_text(f"🗑️ تم إزالة {symbol_to_remove} من قائمة المراقبة.\nالقائمة الحالية: {', '.join(watchlist)}")
        logger.info(f"Admin {update.effective_user.id} removed {symbol_to_remove} from the watchlist.")

    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /remove SYMBOL-USDT")

@admin_only
async def reload_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reloads the configuration from the config file."""
    try:
        # We need to re-import the module to get the latest version of the file
        import importlib
        from src import config as config_module
        importlib.reload(config_module)

        new_config = config_module.get_config()
        context.bot_data['config'] = new_config

        logger.info(f"Admin {update.effective_user.id} reloaded the configuration.")
        await update.message.reply_text("✅ تم إعادة تحميل ملف الإعدادات بنجاح.")

    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}", exc_info=True)
        await update.message.reply_text(f"حدث خطأ أثناء إعادة تحميل الإعدادات: {e}")


# --- Analysis Conversation ---
async def analyze_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the analysis conversation. Asks for a symbol."""
    query = update.callback_query
    await query.answer()

    config = context.bot_data.get('config', get_config())
    ui_cfg = config['ui']
    state_manager: StateManager = context.bot_data['state_manager']
    watchlist = state_manager.get_watchlist()
    cb_data = ui_cfg['CALLBACK_DATA']

    if not watchlist:
        await query.edit_message_text(text="قائمة المراقبة فارغة حاليًا. يمكن للمشرف إضافة عملات باستخدام الأمر /add.")
        # Go back to the main menu gracefully
        await start(update, context)
        return ConversationHandler.END

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
        limit = 1000

        await query.edit_message_text(text=ui_cfg['MESSAGES']['fetching_data'].format(symbol=symbol, timeframe=timeframe))

        data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=limit)

        df = pd.DataFrame(data_dict['data'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)

        analysis_info = analyzer.get_analysis(df, symbol, timeframe)
        formatted_report = format_analysis_from_template(analysis_info, symbol, timeframe)

        await query.message.reply_text(formatted_report, parse_mode='Markdown')

    except DataUnavailableError:
        logger.warning(f"Could not fetch data for {symbol} on {timeframe}.")
        await query.message.reply_text(ui_cfg['MESSAGES']['data_fetch_error'])

    except AnalysisError as e:
        logger.error(f"An analysis error occurred for {symbol} on {timeframe}: {e}", exc_info=False)
        # Use the exception message directly for specific feedback.
        await query.message.reply_text(f"خطأ في التحليل: {e}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during analysis for {symbol} on {timeframe}: {e}", exc_info=True)
        await query.message.reply_text(ui_cfg['MESSAGES']['analysis_error'])

    await start(update, context)
    return ConversationHandler.END

# --- Periodic & Error Handlers ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

async def _run_single_analysis(symbol: str, timeframe: str, application: Application):
    """Helper function to run analysis for a single symbol/timeframe pair."""
    config = application.bot_data.get('config')
    fetcher = DataFetcher(config)
    analyzer = FiboAnalyzer(config, fetcher)
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')

    try:
        data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=300)
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
    except DataUnavailableError:
        logger.warning(f"Periodic analysis: Could not fetch data for {symbol} on {timeframe}.")
    except Exception as e:
        logger.error(f"Error in periodic analysis for {symbol} on {timeframe}: {e}", exc_info=False)


async def run_periodic_analysis(application: Application):
    """Runs analysis periodically and concurrently for all symbols and timeframes."""
    config = application.bot_data.get('config', get_config())
    state_manager: StateManager = application.bot_data.get('state_manager')
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')

    if not state_manager or not admin_chat_id:
        logger.error("StateManager or ADMIN_CHAT_ID not initialized. Skipping periodic analysis.")
        return

    watchlist = state_manager.get_watchlist()
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])

    if not watchlist:
        logger.info("Watchlist is empty. Skipping periodic analysis.")
        return

    logger.info(f"--- Starting Concurrent Periodic Analysis for {len(watchlist)} symbols across {len(timeframes)} timeframes ---")

    tasks = []
    for symbol in watchlist:
        for timeframe in timeframes:
            tasks.append(_run_single_analysis(symbol, timeframe, application))

    await asyncio.gather(*tasks)

    logger.info("--- Concurrent Periodic Analysis Complete ---")

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
    # 1. Load and validate configuration first
    try:
        config = get_config()
        validate_config(config)
        logger.info("Configuration validated successfully.")
    except ValidationError as e:
        logger.critical("!!! CONFIGURATION IS INVALID. BOT WILL NOT START !!!")
        logger.critical("Please check your .env file and src/config.py for the following errors:")
        for error in e.errors():
            loc_str = " -> ".join(map(str, error['loc']))
            logger.critical(f"  - Location: {loc_str} | Message: {error['msg']}")
        return  # Stop execution if config is invalid

    token = config.get('telegram', {}).get('TOKEN')
    # The validator ensures the token exists, so this check is now redundant but safe to keep.
    if not token:
        logger.error("Telegram BOT_TOKEN not found.")
        return

    application = Application.builder().token(token).post_init(post_init).build()

    # Initialize and store the config and state manager in bot_data
    # This makes them accessible and modifiable application-wide
    application.bot_data['config'] = config
    application.bot_data['state_manager'] = StateManager(config)

    ui_cfg = config['ui']
    cb_data = ui_cfg['CALLBACK_DATA']

    # Setup handlers
    conv_handler = setup_conversation_handler(config)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern=f"^{cb_data['main_menu']}$"))
    application.add_handler(CallbackQueryHandler(bot_status, pattern=f"^{cb_data['bot_status']}$"))
    application.add_handler(conv_handler)

    # Add admin command handlers
    application.add_handler(CommandHandler("add", add_symbol))
    application.add_handler(CommandHandler("remove", remove_symbol))
    application.add_handler(CommandHandler("reload", reload_config_command))

    application.add_error_handler(error_handler)

    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
