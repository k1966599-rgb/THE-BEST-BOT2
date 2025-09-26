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
    now = datetime.now()
    text = (
        f"**THE BEST BOT**\n\n"
        f"الحالة: يعمل ✅\n"
        f"__{now.strftime('%Y-%m-%d %H:%M:%S')}__"
    )

    keyboard = [
        [InlineKeyboardButton("📊 تحليل", callback_data='analyze_start')],
        [InlineKeyboardButton("ℹ️ حالة البوت", callback_data='bot_status')],
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

    keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="حالة البوت: يعمل بشكل طبيعي والتحليل الدوري معطل.",
        reply_markup=reply_markup
    )

# --- Analysis Conversation ---
async def analyze_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the analysis conversation. Asks for a symbol."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    watchlist = config.get('trading', {}).get('WATCHLIST', [])

    keyboard = [
        [InlineKeyboardButton(symbol, callback_data=f'symbol_{symbol}') for symbol in watchlist[i:i+2]]
        for i in range(0, len(watchlist), 2)
    ]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="اختر العملة التي تريد تحليلها:",
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
            InlineKeyboardButton("مدى طويل", callback_data='term_long_term'),
            InlineKeyboardButton("مدى متوسط", callback_data='term_medium_term'),
            InlineKeyboardButton("مدى قصير", callback_data='term_short_term'),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data='analyze_start')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"تم اختيار {context.user_data['symbol']}. الآن، اختر مدة التحليل:",
        reply_markup=reply_markup
    )
    return TERM

async def select_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the specific timeframe (e.g., 1H, 4H)."""
    query = update.callback_query
    await query.answer()

    term_key = query.data.split('_', 1)[1]
    context.user_data['term'] = term_key

    config = get_config()
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
    timeframes = timeframe_groups.get(term_key, [])

    if not timeframes:
        await query.edit_message_text(text="خطأ في الإعدادات: لم يتم العثور على أطر زمنية لهذا الاختيار.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f'timeframe_{tf}') for tf in timeframes[i:i+3]]
        for i in range(0, len(timeframes), 3)
    ]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f'symbol_{context.user_data["symbol"]}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"اخترت {term_key.replace('_', ' ')}. الآن، اختر الإطار الزمني:",
        reply_markup=reply_markup
    )
    return TIMEFRAME

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs the analysis and sends the formatted result."""
    query = update.callback_query
    await query.answer()

    context.user_data['timeframe'] = query.data.split('_', 1)[1]
    symbol = context.user_data['symbol']
    timeframe = context.user_data['timeframe']

    await query.edit_message_text(text=f"✅ شكراً لك! جاري تحليل {symbol} على إطار {timeframe}...")

    try:
        config = get_config()
        fetcher = DataFetcher(config)
        analyzer = FiboAnalyzer(config, fetcher)

        # Set a very large limit to fetch all available historical data
        limit = 50000

        await query.edit_message_text(text=f"⏳ شكراً لك! جاري تحميل أقصى بيانات متاحة لعملة {symbol} على إطار {timeframe}...")

        data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=limit)
        if not data_dict or 'data' not in data_dict or not data_dict['data']:
            await query.message.reply_text("عذراً، لم أتمكن من جلب البيانات لهذه العملة. يرجى المحاولة مرة أخرى.")
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
        await query.message.reply_text("حدث خطأ فني أثناء محاولة التحليل. يرجى مراجعة السجلات.")

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
    # scheduler.add_job(run_periodic_analysis, 'interval', minutes=interval, args=[application])
    # scheduler.start()
    logger.info(f"Scheduler is configured but DISABLED. Automatic analysis will not run.")

# --- Conversation Handler Definition ---
# Defined at the module level to allow for easier testing and inspection.
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(analyze_entry, pattern='^analyze_start$')],
    states={
        SYMBOL: [CallbackQueryHandler(select_term, pattern='^symbol_')],
        TERM: [CallbackQueryHandler(select_timeframe, pattern='^term_')],
        TIMEFRAME: [
            CallbackQueryHandler(run_analysis, pattern='^timeframe_'),
            CallbackQueryHandler(select_term, pattern='^symbol_')
        ],
    },
    fallbacks=[CallbackQueryHandler(start, pattern='^main_menu$')],
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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(bot_status, pattern='^bot_status$'))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
