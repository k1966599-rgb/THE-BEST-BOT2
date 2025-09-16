import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher
from src.strategies.fibo_analyzer import FiboAnalyzer
import pandas as pd

# --- Basic Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
SYMBOL, TERM, TIMEFRAME = range(3)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    welcome_text = "مرحباً بك في بوت التحليل الفني للعملات الرقمية!\n\n"
    welcome_text += "استخدم الأمر /analyze لبدء تحليل عملة جديدة.\n"
    welcome_text += "استخدم الأمر /myid لمعرفة Chat ID الخاص بك.\n\n"
    welcome_text += "يقوم البوت بإرسال تنبيهات تلقائية للـ Chat ID المحدد في الإعدادات."
    await update.message.reply_text(welcome_text)

async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the user their chat ID."""
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Your Chat ID is: `{chat_id}`", parse_mode='Markdown')

async def analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for a symbol."""
    config = get_config()
    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    reply_keyboard = [watchlist[i:i + 2] for i in range(0, len(watchlist), 2)]
    reply_keyboard.append(['/cancel'])

    await update.message.reply_text(
        "من فضلك اختر العملة التي تريد تحليلها من القائمة، أو اكتب الرمز (e.g., BTC-USDT).",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SYMBOL

async def received_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected symbol and asks for the analysis term."""
    context.user_data['symbol'] = update.message.text
    reply_keyboard = [["Long Term", "Medium Term", "Short Term"], ['/cancel']]
    await update.message.reply_text(
        f"تم اختيار {update.message.text}. الآن، من فضلك اختر مدة التحليل.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return TERM

async def received_term(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the analysis term and asks for the timeframe."""
    term = update.message.text
    context.user_data['term'] = term
    config = get_config()
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
    timeframes = timeframe_groups.get(term.lower().replace(" ", "_"), [])
    if not timeframes:
        await update.message.reply_text("خيار غير صالح. تم إلغاء العملية.")
        return ConversationHandler.END
    reply_keyboard = [timeframes[i:i + 3] for i in range(0, len(timeframes), 3)]
    reply_keyboard.append(['/cancel'])
    await update.message.reply_text(
        f"اخترت {term}. الآن، من فضلك اختر الإطار الزمني (Timeframe).",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return TIMEFRAME

async def received_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the timeframe, runs the analysis, and sends the result."""
    context.user_data['timeframe'] = update.message.text
    symbol = context.user_data['symbol']
    timeframe = context.user_data['timeframe']

    await update.message.reply_text(
        f"شكراً لك! جاري تحليل {symbol} على إطار {timeframe}...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        config = get_config()
        fetcher = DataFetcher(config)
        analyzer = FiboAnalyzer(config)
        data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=300)
        if not data_dict or 'data' not in data_dict or not data_dict['data']:
            await update.message.reply_text("عذراً، لم أتمكن من جلب البيانات لهذه العملة. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
        df = pd.DataFrame(data_dict['data'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        analysis_info = analyzer.get_analysis(df)
        signal = analysis_info.get('signal', 'N/A')
        reason = analysis_info.get('reason', 'No reason provided.')
        analysis_result = f"--- تحليل {symbol} | {timeframe} ---\n\n"
        analysis_result += f"الإشارة الحالية: **{signal}**\n"
        analysis_result += f"السبب: {reason}\n"
        await update.message.reply_text(analysis_result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"An error occurred during analysis for {symbol} on {timeframe}: {e}")
        await update.message.reply_text("حدث خطأ أثناء محاولة التحليل. يرجى مراجعة السجلات.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# --- Periodic Analysis Job ---
async def run_periodic_analysis(application: Application):
    """
    This function is the core of the continuous analysis loop.
    It runs analysis periodically for all symbols and timeframes from the config
    and sends a notification to the admin chat ID if a BUY or SELL signal is found.
    """
    config = get_config()
    fetcher = DataFetcher(config)
    analyzer = FiboAnalyzer(config)
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')

    if not admin_chat_id:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID is not set. Periodic analysis alerts will be skipped.")
        return

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])

    logger.info(f"--- Starting Periodic Analysis for {len(watchlist)} symbols ---")

    for symbol in watchlist:
        for timeframe in timeframes:
            logger.info(f"Analyzing {symbol} on {timeframe}...")
            try:
                data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=300)
                if not data_dict or 'data' not in data_dict or not data_dict['data']:
                    logger.warning(f"Could not fetch data for {symbol} on {timeframe}. Skipping.")
                    continue

                df = pd.DataFrame(data_dict['data'])
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                analysis_info = analyzer.get_analysis(df)
                signal = analysis_info.get('signal', 'N/A')

                if signal in ['BUY', 'SELL']:
                    reason = analysis_info.get('reason', 'No reason provided.')
                    message = f"🚨 **Automatic Alert** 🚨\n\n"
                    message += f"**Symbol:** {symbol}\n"
                    message += f"**Timeframe:** {timeframe}\n"
                    message += f"**Signal:** {signal}\n"
                    message += f"**Reason:** {reason}"
                    await application.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='Markdown')
                    logger.info(f"Sent '{signal}' alert for {symbol} on {timeframe} to admin.")

            except Exception as e:
                logger.error(f"Error during periodic analysis of {symbol} on {timeframe}: {e}")

            await asyncio.sleep(2) # Be respectful of API limits

    logger.info("--- Periodic Analysis Complete ---")

async def post_init(application: Application) -> None:
    """
    This coroutine is executed by the Application after it has been initialized,
    but before it starts polling. It's the ideal place to set up background tasks
    like the scheduler, ensuring they run within the same asyncio event loop.
    """
    config = get_config()
    interval_minutes = config.get('trading', {}).get('ANALYSIS_INTERVAL_MINUTES', 15)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_periodic_analysis, 'interval', minutes=interval_minutes, args=[application])
    scheduler.start()
    logger.info(f"Scheduler started. Analysis will run every {interval_minutes} minutes.")

def main() -> None:
    """Start the bot."""
    config = get_config()
    token = config.get('telegram', {}).get('TOKEN')

    if not token:
        logger.error("Telegram BOT_TOKEN not found in .env file. The bot cannot start.")
        return

    # Using post_init ensures the scheduler runs in the same asyncio loop as the bot.
    application = Application.builder().token(token).post_init(post_init).build()

    # --- Conversation Handler for /analyze ---
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("analyze", analyze_start)],
        states={
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_symbol)],
            TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_term)],
            TIMEFRAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_timeframe)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # --- Register Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", show_chat_id))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
