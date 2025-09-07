import logging
import re
import threading
import time
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from .base_notifier import BaseNotifier
from ..data.base_fetcher import BaseDataFetcher
from ..analysis.orchestrator import AnalysisOrchestrator
from ..decision_engine.engine import DecisionEngine
from ..utils.report_generator import generate_final_report_text
from ..config import WATCHLIST, get_config

# --- Logging Setup ---
class TokenFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'msg'):
            record.msg = re.sub(r'bot(\d+):[A-Za-z0-9_-]+', r'bot\1:***TOKEN_REDACTED***', str(record.msg))
        return True

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
for handler in logging.root.handlers:
    handler.addFilter(TokenFilter())
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class InteractiveTelegramBot(BaseNotifier):
    """
    An interactive Telegram bot for running analysis on demand.
    This class is responsible for the UI and user interaction, but delegates
    the core logic (fetching, analysis, decision) to other components.
    """

    def __init__(self, config: Dict, fetcher: BaseDataFetcher, orchestrator: AnalysisOrchestrator, decision_engine: DecisionEngine):
        super().__init__(config.get('telegram', {}))
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.decision_engine = decision_engine
        self.bot_state = {"is_active": True}
        self.token = self.config.get('BOT_TOKEN')

    def _get_start_message_text(self) -> str:
        # ... (UI helper methods remain largely the same)
        status = "🟢 متصل وجاهز للعمل" if self.bot_state["is_active"] else "🔴 متوقف"
        return f"💎 <b>THE BEST BOT</b> 💎\n<b>حالة النظام:</b> {status}"

    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("▶️ تشغيل", callback_data="start_bot"), InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
                    [InlineKeyboardButton("🔍 تحليل", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_coin_list_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton(coin, callback_data=f"coin_{coin}") for coin in WATCHLIST[i:i+2]] for i in range(0, len(WATCHLIST), 2)]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")])
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_timeframe_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
            [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
            [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
            [InlineKeyboardButton("🔙 رجوع لقائمة العملات", callback_data="analyze_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    def _run_analysis_for_request(self, symbol: str, timeframes: list, analysis_type: str) -> str:
        """
        This method replaces the old, tightly-coupled analysis call.
        It uses the injected orchestrator and decision engine to get a result.
        """
        logger.info(f"Bot request: Starting analysis for {symbol} on timeframes: {timeframes}...")
        all_results = []
        for tf in timeframes:
            # Re-using the pipeline from app.py, this could be further refactored
            try:
                okx_symbol = symbol.replace('/', '-')
                api_timeframe = tf.replace('d', 'D').replace('h', 'H')
                df = self.fetcher.fetch_historical_data(symbol=okx_symbol, timeframe=api_timeframe, days_to_fetch=365)
                if not df:
                    raise ConnectionError(f"Failed to fetch data for {symbol} on {tf}")

                analysis_results = self.orchestrator.run(df)
                recommendation = self.decision_engine.make_recommendation(analysis_results)
                recommendation['timeframe'] = tf
                recommendation['symbol'] = symbol
                all_results.append({'success': True, 'recommendation': recommendation})
            except Exception as e:
                logger.exception(f"Analysis failed for {symbol} on {tf} in bot request.")
                all_results.append({'success': False, 'timeframe': tf, 'error': str(e)})

        successful_recs = [r['recommendation'] for r in all_results if r.get('success')]
        if not successful_recs:
            return f"❌ تعذر تحليل {symbol} لجميع الأطر الزمنية المطلوبة."

        ranked_recs = self.decision_engine.rank_recommendations(successful_recs)
        return generate_final_report_text(symbol=symbol, analysis_type=analysis_type, ranked_results=ranked_recs)

    async def _main_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        if callback_data == "start_menu":
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
        elif callback_data == "start_bot":
            self.bot_state["is_active"] = True
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
        elif callback_data == "stop_bot":
            self.bot_state["is_active"] = False
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
        elif callback_data == "analyze_menu":
            if not self.bot_state["is_active"]:
                await query.message.reply_text("البوت متوقف حاليًا. يرجى الضغط على 'تشغيل' أولاً.")
                return
            await query.edit_message_text(text="الرجاء اختيار عملة للتحليل:", reply_markup=self._get_coin_list_keyboard())
        elif callback_data.startswith("coin_"):
            symbol = callback_data.split("_", 1)[1]
            await query.edit_message_text(text=f"اختر نوع التحليل لـ <code>{symbol}</code>:", reply_markup=self._get_analysis_timeframe_keyboard(symbol), parse_mode='HTML')
        elif callback_data.startswith("analyze_"):
            parts = callback_data.split("_")
            analysis_scope = parts[1]
            symbol = "_".join(parts[2:])

            analysis_map = {
                "long": ("استثمار طويل المدى", get_config()['trading']['TIMEFRAME_GROUPS']['long']),
                "medium": ("تداول متوسط المدى", get_config()['trading']['TIMEFRAME_GROUPS']['medium']),
                "short": ("مضاربة سريعة", get_config()['trading']['TIMEFRAME_GROUPS']['short'])
            }
            analysis_name, timeframes = analysis_map.get(analysis_scope, ("غير محدد", []))

            await query.edit_message_text(text=f"جاري إعداد <b>{analysis_name}</b> لـ <code>{symbol}</code>...", parse_mode='HTML')

            try:
                # Run analysis in a separate thread to avoid blocking the bot
                final_report = await context.application.create_task(
                    self._run_analysis_for_request,
                    symbol, timeframes, analysis_name
                )
                await query.message.reply_text(text=final_report, parse_mode='HTML')
                await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
            except Exception as e:
                logger.exception(f"Unhandled error in bot callback for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}", parse_mode='HTML')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        # This method is for simple, non-interactive sending.
        # The interactive bot doesn't use it, but it's here to satisfy the interface.
        logger.info("The `send` method is not implemented for the interactive bot. Use `start()` instead.")
        return False

    def start(self):
        """Starts the interactive Telegram bot."""
        if not self.token:
            logger.error("CRITICAL: Telegram bot token not found. The interactive bot cannot start.")
            return

        application = Application.builder().token(self.token).build()
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))

        logger.info("🤖 Interactive bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
