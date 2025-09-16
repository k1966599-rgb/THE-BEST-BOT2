import logging
import re
import time
import anyio
import asyncio
import uuid
from typing import Dict, Any, List, Tuple
import pandas as pd

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from .base_notifier import BaseNotifier
from ..data_retrieval.base_fetcher import BaseDataFetcher
from ..analysis.orchestrator import AnalysisOrchestrator
from ..decision_engine.engine import DecisionEngine
from ..reporting.report_builder import ReportBuilder
from ..config import get_config
from ..utils.data_preprocessor import standardize_dataframe_columns
from ..decision_engine.trade_setup import TradeSetup
from ..monitoring.trade_monitor import TradeMonitor
from .telegram_sender import SimpleTelegramNotifier


class TokenFilter(logging.Filter):
    """A logging filter to redact the Telegram bot token from log messages."""
    def filter(self, record):
        """Filters the log record, redacting the bot token."""
        if hasattr(record, 'msg'):
            record.msg = re.sub(r'bot(\d+):[A-Za-z0-9_-]+', r'bot\1:***TOKEN_REDACTED***', str(record.msg))
        return True
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
for handler in logging.root.handlers:
    handler.addFilter(TokenFilter())
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class InteractiveTelegramBot(BaseNotifier):
    """The main interactive Telegram bot class."""
    def __init__(self, config: Dict, fetcher: BaseDataFetcher):
        self.full_config = config
        super().__init__(config.get('telegram', {}))
        self.fetcher = fetcher
        self.decision_engine = DecisionEngine(config)
        self.report_builder = ReportBuilder(config)
        self.bot_state = {"is_active": True}
        self.pending_analyses: Dict[str, List[Dict]] = {}
        self.token = self.config.get('BOT_TOKEN')
        self.bot = None

        alert_notifier = SimpleTelegramNotifier(config.get('telegram', {}))
        self.trade_monitor = TradeMonitor(
            config=config,
            fetcher=fetcher,
            notifier=alert_notifier
        )

    def _get_start_message_text(self) -> str:
        status = "🟢 متصل وجاهز" if self.bot_state["is_active"] else "🔴 متوقف"
        return f"💎 <b>أفضل بوت</b> 💎\n<b>حالة النظام:</b> {status}"

    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("▶️ بدء", callback_data="start_bot"), InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
                    [InlineKeyboardButton("🔍 تحليل", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_coin_list_keyboard(self) -> InlineKeyboardMarkup:
        watchlist = self.full_config.get('trading', {}).get('WATCHLIST', [])
        keyboard = [[InlineKeyboardButton(coin, callback_data=f"coin_{coin}") for coin in watchlist[i:i+2]] for i in range(0, len(watchlist), 2)]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")])
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_timeframe_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
                    [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
                    [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
                    [InlineKeyboardButton("🔙 رجوع إلى قائمة العملات", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_follow_keyboard(self, analysis_id: str) -> InlineKeyboardMarkup:
        keyboard = [[
            InlineKeyboardButton("متابعة", callback_data=f"follow_{analysis_id}"),
            InlineKeyboardButton("تجاهل", callback_data="ignore")
        ]]
        return InlineKeyboardMarkup(keyboard)

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    async def _run_analysis_for_request(self, chat_id: int, symbol: str, timeframes: list, analysis_type: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        logger.info(f"Bot request: Starting analysis for {symbol} on timeframes: {timeframes}...")
        all_results = []
        current_price = 0
        for tf in timeframes:
            try:
                okx_symbol = symbol.replace('/', '-')
                api_timeframe = tf.replace('d', 'D').replace('h', 'H')
                historical_data_wrapper = await anyio.to_thread.run_sync(
                    self.fetcher.fetch_historical_data, okx_symbol, api_timeframe
                )
                if not historical_data_wrapper or not historical_data_wrapper.get('data'):
                    raise ConnectionError(f"Failed to fetch data for {symbol} on {tf}")

                df = pd.DataFrame(historical_data_wrapper['data'])
                df = standardize_dataframe_columns(df)
                df.set_index('timestamp', inplace=True)

                if not df.empty:
                    current_price = df['close'].iloc[-1]

                # Initialize analysis modules for the current timeframe
                from ..analysis import (
                    TrendAnalysis, NewSupportResistanceAnalysis, FibonacciAnalysis,
                    ClassicPatterns, PivotDetector, QuantileChannelAnalysis
                )
                from ..indicators.technical_score import TechnicalIndicators
                from ..indicators.volume_profile import VolumeProfileAnalysis

                # 1. Get timeframe-specific pivots first
                pivot_detector = PivotDetector(config=self.full_config, timeframe=tf)
                pivots = pivot_detector.analyze(df)
                highs, lows = pivots['highs'], pivots['lows']

                analysis_modules = [
                    TechnicalIndicators(config=self.full_config, timeframe=tf),
                    TrendAnalysis(config=self.full_config, timeframe=tf),
                    QuantileChannelAnalysis(config=self.full_config, timeframe=tf),
                    NewSupportResistanceAnalysis(config=self.full_config, timeframe=tf),
                    FibonacciAnalysis(config=self.full_config, timeframe=tf),
                    ClassicPatterns(config=self.full_config, timeframe=tf),
                    VolumeProfileAnalysis(config=self.full_config, timeframe=tf)
                ]
                orchestrator = AnalysisOrchestrator(analysis_modules)
                analysis_results = orchestrator.run(df, highs=highs, lows=lows)
                recommendation = self.decision_engine.make_recommendation(analysis_results, df, symbol, tf, chat_id)
                recommendation['current_price'] = current_price
                all_results.append(recommendation)
            except Exception as e:
                logger.exception(f"Unhandled error during analysis for {symbol} on Bot request.")
                return [{"error": f"❌ An internal error occurred while analyzing {symbol} on {tf}."}], []

        if not all_results:
            return [{"error": f"❌ Could not analyze {symbol} for any of the requested timeframes."}], []

        ranked_recs = self.decision_engine.rank_recommendations(all_results)
        general_info = {'symbol': symbol, 'analysis_type': analysis_type, 'current_price': current_price, 'timeframes': timeframes}
        report_messages = self.report_builder.build_report(ranked_results=ranked_recs, general_info=general_info)
        return report_messages, ranked_recs

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        MAX_LENGTH = 4096
        if len(text) <= MAX_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return

        parts = text.split('\n\n')
        current_message = ""
        for part in parts:
            if len(current_message) + len(part) + 2 > MAX_LENGTH:
                await self.bot.send_message(chat_id=chat_id, text=current_message, **kwargs)
                current_message = part
            else:
                current_message += "\n\n" + part
        if current_message:
            await self.bot.send_message(chat_id=chat_id, text=current_message, **kwargs)
        await asyncio.sleep(0.5)

    async def _main_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        if callback_data == "start_menu":
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
        elif callback_data == "analyze_menu":
            await query.edit_message_text(text="الرجاء اختيار عملة لتحليلها:", reply_markup=self._get_coin_list_keyboard())
        elif callback_data.startswith("coin_"):
            symbol = callback_data.split("_", 1)[1]
            await query.edit_message_text(text=f"اختر نوع التحليل لـ <code>{symbol}</code>:", reply_markup=self._get_analysis_timeframe_keyboard(symbol), parse_mode='HTML')
        elif callback_data.startswith("analyze_"):
            parts = callback_data.split("_")
            analysis_scope, symbol = parts[1], "_".join(parts[2:])
            # Use the centralized map from the report builder
            analysis_name = self.report_builder.analysis_type_map.get(f"{analysis_scope}_term")
            timeframes = self.full_config['trading']['TIMEFRAME_GROUPS'].get(f"{analysis_scope}_term", [])
            if not symbol or not timeframes:
                 await query.message.reply_text("خطأ: لم يتم تحديد العملة أو نوع التحليل بشكل صحيح.")
                 return

            await query.edit_message_text(text=f"جاري تحضير <b>{analysis_name}</b> لـ <code>{symbol}</code>...", parse_mode='HTML')
            try:
                chat_id = query.message.chat_id
                report_messages, ranked_recs = await self._run_analysis_for_request(chat_id, symbol, timeframes, analysis_name)

                if not report_messages or (report_messages and report_messages[0].get("error")):
                    error_message = report_messages[0].get("error") if report_messages else "حدث خطأ غير معروف."
                    await query.message.reply_text(error_message)
                    return

                analysis_id = None
                if any(r.get('trade_setup') for r in ranked_recs):
                    analysis_id = str(uuid.uuid4())
                    self.pending_analyses[analysis_id] = ranked_recs

                for message_info in report_messages:
                    reply_markup = None
                    if message_info.get("keyboard") == "follow_ignore" and analysis_id:
                        reply_markup = self._get_follow_keyboard(analysis_id)

                    if message_info.get("content"):
                        await self._send_long_message(chat_id=chat_id, text=message_info["content"], parse_mode='HTML', reply_markup=reply_markup)

                if not any(msg.get("keyboard") for msg in report_messages):
                     await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

            except Exception as e:
                logger.exception(f"Unhandled error in bot callback for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}", parse_mode='HTML')

        elif callback_data.startswith("follow_"):
            analysis_id = callback_data.split("_", 1)[1]
            ranked_recs = self.pending_analyses.pop(analysis_id, None)

            if ranked_recs:
                trades_added = 0
                for rec in ranked_recs:
                    if rec.get('trade_setup'):
                        self.trade_monitor.add_trade(rec)
                        trades_added += 1

                if trades_added > 0:
                    await query.edit_message_text(text=f"✅ تمت إضافة {trades_added} توصية للمراقبة.")
                else:
                    await query.edit_message_text(text="❌ لم يتم العثور على توصيات قابلة للمتابعة في هذا التحليل.")
            else:
                await query.edit_message_text(text="❌ انتهت صلاحية التحليل أو تم استخدامه بالفعل. يرجى طلب تحليل جديد.")

            await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

        elif callback_data == "ignore":
            await query.edit_message_text(text="تم تجاهل التحليل.")
            await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        logger.info("The `send` method is not implemented for the interactive bot. Use `start()` instead.")
        return False

    async def _post_init(self, application: Application):
        self.trade_monitor.notifier.bot = application.bot
        application.create_task(self.trade_monitor.run_monitoring_loop())

    def start(self):
        if not self.token:
            logger.error("FATAL: Telegram Bot Token not found.")
            return
        application = Application.builder().token(self.token).post_init(self._post_init).build()
        self.bot = application.bot
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))
        logger.info("🤖 Interactive Bot and Trade Monitor are starting...")
        application.run_polling()
