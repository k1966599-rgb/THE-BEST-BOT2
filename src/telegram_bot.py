import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
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
from src.utils.chart_generator import generate_analysis_chart
from src.localization import get_text
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

    # Final, simplified, plain-text version of the welcome message.
    header = "             THE BEST BOT             "
    status = "الحالة: يعمل"
    time_info = f"التاريخ والوقت: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    # The text is constructed directly without any markdown or localization keys.
    text = f"{header}\n\n{status}\n{time_info}"

    keyboard = [
        [InlineKeyboardButton("بدء التحليل", callback_data='analyze_start')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Simplified send/edit logic without parse modes.
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)

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
    keyboard.append([InlineKeyboardButton("العودة", callback_data='main_menu')])
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
            InlineKeyboardButton("طويل المدى", callback_data='term_long_term'),
            InlineKeyboardButton("متوسط المدى", callback_data='term_medium_term'),
            InlineKeyboardButton("قصير المدى", callback_data='term_short_term'),
        ],
        [InlineKeyboardButton("العودة", callback_data='analyze_start')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"اختر فئة الفريمات للعملة {context.user_data['symbol']}:",
        reply_markup=reply_markup
    )
    return TERM

async def back_to_term_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Back' button from the timeframe selection, returning to term selection."""
    query = update.callback_query
    await query.answer()

    symbol = context.user_data.get('symbol', 'العملة')

    keyboard = [
        [
            InlineKeyboardButton("طويل المدى", callback_data='term_long_term'),
            InlineKeyboardButton("متوسط المدى", callback_data='term_medium_term'),
            InlineKeyboardButton("قصير المدى", callback_data='term_short_term'),
        ],
        [InlineKeyboardButton("العودة", callback_data='analyze_start')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"اختر فئة الفريمات للعملة {symbol}:",
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
        await query.edit_message_text(text="خطأ: لم يتم تكوين مجموعات الأطر الزمنية بشكل صحيح.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f'timeframe_{tf}') for tf in timeframes[i:i+3]]
        for i in range(0, len(timeframes), 3)
    ]
    # The callback for the back button should go to the previous state (term selection)
    keyboard.append([InlineKeyboardButton("العودة", callback_data='back_to_term')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    term_map = {"long_term": "طويل المدى", "medium_term": "متوسط المدى", "short_term": "قصير المدى"}
    term_text = term_map.get(term_key, term_key.replace('_', ' '))

    await query.edit_message_text(
        text=f"اختر الإطار الزمني للفئة '{term_text}':",
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

    df.dropna(subset=['timestamp', 'open', 'high', 'low', 'close', 'volume'], inplace=True)
    return df

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs the Multi-Timeframe-Aware analysis and sends the formatted result."""
    query = update.callback_query
    await query.answer()

    context.user_data['timeframe'] = query.data.split('_', 1)[1]
    symbol = context.user_data['symbol']
    timeframe = context.user_data['timeframe']
    config = context.bot_data['config']
    fetcher = DataFetcher(config)

    trading_config = config.get('trading', {})
    candle_limits = trading_config.get('CANDLE_FETCH_LIMITS', {})
    hierarchy = trading_config.get('TIMEFRAME_HIERARCHY', {})

    limit = candle_limits.get(timeframe, candle_limits.get('default', 1000))
    parent_timeframe = hierarchy.get(timeframe)
    higher_tf_trend_info = None

    try:
        if parent_timeframe:
            await query.edit_message_text(text=f"جاري جلب بيانات الإطار الزمني الأعلى ({parent_timeframe})...")
            parent_limit = candle_limits.get(parent_timeframe, candle_limits.get('default', 1000))
            parent_df = await _fetch_and_prepare_data(fetcher, symbol, parent_timeframe, limit=parent_limit)

            parent_analyzer = FiboAnalyzer(config, fetcher, timeframe=parent_timeframe)
            parent_analysis = parent_analyzer.get_analysis(parent_df, symbol, parent_timeframe)
            higher_tf_trend_info = {
                'trend': parent_analysis.get('trend', 'N/A'),
                'timeframe': parent_timeframe
            }

        await query.edit_message_text(text=f"جاري جلب البيانات لـ {symbol} على فريم {timeframe}...")
        df = await _fetch_and_prepare_data(fetcher, symbol, timeframe, limit=limit)

        await query.edit_message_text(text=f"جاري تحليل {symbol} على فريم {timeframe}...")

        analyzer = FiboAnalyzer(config, fetcher, timeframe=timeframe)
        analysis_info = analyzer.get_analysis(df, symbol, timeframe, higher_tf_trend_info=higher_tf_trend_info)

        # Generate the chart
        await query.edit_message_text(text="جاري إنشاء الرسم البياني...")
        chart_bytes = generate_analysis_chart(df, analysis_info, symbol)

        # Format the text report
        formatted_report = format_analysis_from_template(analysis_info, symbol, timeframe)

        if chart_bytes:
            # Send the photo directly from the bytes in memory
            await query.message.reply_photo(photo=chart_bytes, caption=formatted_report)
        else:
            # Fallback to sending text only if chart generation fails
            await query.message.reply_text(formatted_report)

    except InsufficientDataError as e:
        logger.warning(f"Caught InsufficientDataError for {symbol} on {timeframe}: {e}")
        if hasattr(e, 'required') and hasattr(e, 'available'):
            await query.message.reply_text(
                f"لا توجد بيانات كافية لـ {symbol} على فريم {timeframe}. "
                f"المطلوب: {e.required} شمعة، المتاح: {e.available} شمعة."
            )
        else:
            await query.message.reply_text(
                f"لا توجد بيانات تاريخية كافية للتحليل لـ {symbol} على فريم {timeframe}."
            )
    except (APIError, NetworkError) as e:
        logger.error(f"Detailed network error for {symbol} on {timeframe}: {e}")
        # Provide a more detailed error message to the user for debugging
        detailed_error_message = f"فشل الاتصال بالـ API.\n\n**السبب:**\n`{e}`\n\nيرجى التحقق من إعدادات الـ API أو المحاولة مرة أخرى."
        await query.message.reply_text(detailed_error_message)
    except Exception as e:
        logger.error(f"An unexpected error occurred during analysis for {symbol} on {timeframe}: {e}", exc_info=True)
        await query.message.reply_text("حدث خطأ غير متوقع. يرجى مراجعة سجلات الأخطاء.")

    await start(update, context)
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

async def run_periodic_analysis(application: Application):
    """Runs analysis periodically and sends formatted alerts."""
    config = application.bot_data['config']
    fetcher = DataFetcher(config)
    admin_chat_id = config.get('telegram', {}).get('ADMIN_CHAT_ID')
    if not admin_chat_id:
        logger.warning(get_text("warning_no_admin_id"))
        return

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])
    candle_limits = config.get('trading', {}).get('CANDLE_FETCH_LIMITS', {})
    logger.info(get_text("periodic_start_log").format(count=len(watchlist)))

    for symbol in watchlist:
        for timeframe in timeframes:
            try:
                analyzer = FiboAnalyzer(config, fetcher, timeframe=timeframe)
                limit = candle_limits.get(timeframe, candle_limits.get('default', 1000))
                df = await _fetch_and_prepare_data(fetcher, symbol, timeframe, limit=limit)
                analysis_info = analyzer.get_analysis(df, symbol, timeframe)

                if analysis_info.get('signal') in ['BUY', 'SELL']:
                    report = format_analysis_from_template(analysis_info, symbol, timeframe)
                    chart_bytes = generate_analysis_chart(df, analysis_info, symbol)

                    if chart_bytes:
                        await application.bot.send_photo(
                            chat_id=admin_chat_id,
                            photo=chart_bytes,
                            caption=report
                        )
                    else:
                        # Fallback to text if chart generation fails
                        await application.bot.send_message(chat_id=admin_chat_id, text=report)

                    logger.info(get_text("periodic_sent_alert_log").format(
                        signal=analysis_info['signal'], symbol=symbol, timeframe=timeframe
                    ))
            except Exception as e:
                logger.error(f"Error in periodic analysis for {symbol} on {timeframe}: {e}")
            await asyncio.sleep(2)
    logger.info(get_text("periodic_end_log"))

async def post_init(application: Application) -> None:
    """Initializes the background scheduler and loads config."""
    config = application.bot_data.get('config', get_config())
    application.bot_data['config'] = config

    # --- Scheduler Setup ---
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Get analysis interval from config, default to 4 hours
    interval_hours = config.get('analysis_interval_hours', 4)

    # Schedule the periodic analysis job
    scheduler.add_job(
        run_periodic_analysis,
        "interval",
        hours=interval_hours,
        args=[application],
        name="periodic_analysis_job"
    )

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started. Periodic analysis will run every {interval_hours} hours.")

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(analyze_entry, pattern='^analyze_start$')],
    states={
        SYMBOL: [CallbackQueryHandler(select_term, pattern='^symbol_')],
        TERM: [CallbackQueryHandler(select_timeframe, pattern='^term_')],
        TIMEFRAME: [
            CallbackQueryHandler(run_analysis, pattern='^timeframe_'),
            CallbackQueryHandler(back_to_term_selection, pattern='^back_to_term$')
        ],
    },
    fallbacks=[CallbackQueryHandler(start, pattern='^main_menu$')],
    per_message=False
)