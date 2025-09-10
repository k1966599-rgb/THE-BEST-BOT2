import logging
import re
import asyncio
import uuid
from typing import Dict, Any, List
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# --- New Imports ---
from .base_notifier import BaseNotifier
from src.analysis.models import AnalysisReport, TimeframeAnalysis, TechnicalPattern, Support, Resistance, ExecutiveSummary, ConfirmedTrade
from src.analysis.tracker import AnalysisTracker
from src.notifiers.analysis_formatter import format_full_analysis_messages
from src.config import WATCHLIST, get_config
from src.data.base_fetcher import BaseDataFetcher

# --- Logging Setup (remains the same) ---
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


# --- THE REFACTORED BOT CLASS ---
class InteractiveTelegramBot(BaseNotifier):
    def __init__(self, config: Dict, fetcher: BaseDataFetcher):
        super().__init__(config.get('telegram', {}))
        self.fetcher = fetcher
        self.bot_state = {"is_active": True}
        self.token = self.config.get('BOT_TOKEN')
        self.bot = None
        self.tracker = AnalysisTracker()

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        logger.warning(
            "The `send` method was called on the interactive bot, but it's not designed for direct sending. "
            "Use `start()` to run the bot."
        )
        return False

    # --- Keyboard Layouts (Refactored) ---
    def _get_start_message_text(self) -> str:
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

    def _get_analysis_type_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
            [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
            [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
            [InlineKeyboardButton("🔙 رجوع لقائمة العملات", callback_data="analyze_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_follow_keyboard(self, report_id: str) -> InlineKeyboardMarkup:
        keyboard = [[
            InlineKeyboardButton("📈 متابعة", callback_data=f"follow:{report_id}"),
            InlineKeyboardButton("🗑️ تجاهل", callback_data=f"ignore:{report_id}")
        ]]
        return InlineKeyboardMarkup(keyboard)

    # --- Placeholder Analysis Generator (Updated) ---
    def _create_mock_analysis(self, pair: str, analysis_type: str, timeframes: List[str]) -> AnalysisReport:
        report_id = str(uuid.uuid4())
        timeframe_analyses = []
        for tf in timeframes:
            analysis = TimeframeAnalysis(
                timeframe=tf, current_price=111550.0,
                pattern=TechnicalPattern(name="نموذج قيد التحليل", status="قيد التكوين", activation_condition=f"اختراق المقاومة A", invalidation_condition=f"كسر الدعم B", target=12345.0),
                supports=[Support(type="دعم رئيسي", level=110000.0, strength="قوي")],
                resistances=[Resistance(type="مقاومة رئيسية", level=115000.0, strength="قوية")]
            )
            timeframe_analyses.append(analysis)
        summary_text = f"ملخص لـ {len(timeframes)} إطارات زمنية."
        summary = ExecutiveSummary(
            short_term_summary=summary_text, medium_term_summary=summary_text, long_term_summary=summary_text,
            critical_points={"resistance_breakout": "مراقبة اختراق المقاومات", "support_breakdown": "مراقبة كسر الدعوم"}
        )
        trade = ConfirmedTrade(
            entry_price_condition="عند تحقق شروط التفعيل", targets=[120000.0, 125000.0],
            stop_loss_condition="عند تحقق شروط الإلغاء", strategy_details="دمج الإشارات من جميع الإطارات الزمنية."
        )
        return AnalysisReport(
            report_id=report_id, pair=pair, analysis_type=analysis_type,
            timeframe_analyses=timeframe_analyses, summary=summary, confirmed_trade=trade
        )

    # --- Core Logic (Refactored) ---
    async def _generate_and_send_new_analysis(self, chat_id: int, symbol: str, analysis_type: str, timeframes: List[str]):
        report = self._create_mock_analysis(symbol, analysis_type, timeframes)
        self.tracker.follow_analysis(report)
        self.tracker.unfollow_analysis(report.report_id)
        formatted_messages = format_full_analysis_messages(report)
        timeframe_msgs = formatted_messages["timeframe_messages"]
        summary_msg = formatted_messages["summary_message"]
        for msg in timeframe_msgs:
            await self._send_long_message(chat_id, msg, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.5)
        keyboard = self._get_analysis_follow_keyboard(report.report_id)
        await self._send_long_message(chat_id, summary_msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        MAX_LENGTH = 4096
        if len(text) <= MAX_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return
        parts = [text[i:i + MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
        for part in parts:
            await self.bot.send_message(chat_id=chat_id, text=part, **kwargs)
            await asyncio.sleep(0.5)

    # --- Command and Callback Handlers (Refactored) ---
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.HTML)

    async def _main_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        if callback_data == "start_menu":
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.HTML)
        elif callback_data == "start_bot":
            self.bot_state["is_active"] = True
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.HTML)
        elif callback_data == "stop_bot":
            self.bot_state["is_active"] = False
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.HTML)
        elif callback_data == "analyze_menu":
            await query.edit_message_text(text="الرجاء اختيار عملة للتحليل:", reply_markup=self._get_coin_list_keyboard())
        elif callback_data.startswith("coin_"):
            symbol = callback_data.split("_", 1)[1]
            await query.edit_message_text(text=f"اختر نوع التحليل لـ <code>{symbol}</code>:", reply_markup=self._get_analysis_type_keyboard(symbol), parse_mode=ParseMode.HTML)
        elif callback_data.startswith("analyze_"):
            if not self.bot_state["is_active"]:
                await query.message.reply_text("البوت متوقف حاليًا. يرجى الضغط على 'تشغيل' أولاً.")
                return
            parts = callback_data.split("_")
            analysis_scope = parts[1]
            symbol = "_".join(parts[2:])
            config = get_config()
            analysis_map = {
                "long": ("استثمار طويل المدى", config['trading']['TIMEFRAME_GROUPS']['long']),
                "medium": ("تداول متوسط المدى", config['trading']['TIMEFRAME_GROUPS']['medium']),
                "short": ("مضاربة سريعة", config['trading']['TIMEFRAME_GROUPS']['short'])
            }
            analysis_type, timeframes = analysis_map.get(analysis_scope, ("غير محدد", []))
            if not symbol or not timeframes:
                 await query.message.reply_text("خطأ: لم يتم تحديد العملة أو نوع التحليل بشكل صحيح.")
                 return
            await query.edit_message_text(text=f"جاري إعداد <b>{analysis_type}</b> لـ <code>{symbol}</code>...", parse_mode=ParseMode.HTML)
            try:
                await self._generate_and_send_new_analysis(
                    chat_id=query.message.chat_id, symbol=symbol,
                    analysis_type=analysis_type, timeframes=timeframes
                )
            except Exception as e:
                logger.exception(f"Error generating new analysis for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}")
        elif callback_data.startswith("follow:"):
            report_id = callback_data.split(":", 1)[1]
            report = self.tracker.get_analysis_by_id(report_id)
            if report:
                report.is_followed = True
                self.tracker.update_analysis(report)
                await query.edit_message_text(text=f"✅ <b>تمت إضافة تحليل {report.pair} للمتابعة اللحظية.</b>", parse_mode=ParseMode.HTML, reply_markup=None)
            else:
                await query.edit_message_text(text="❌ لم يتم العثور على التحليل. ربما انتهت صلاحيته.", reply_markup=None)
        elif callback_data.startswith("ignore:"):
            report_id = callback_data.split(":", 1)[1]
            self.tracker.unfollow_analysis(report_id)
            await query.edit_message_text(text="<b>تم تجاهل التحليل.</b>", parse_mode=ParseMode.HTML, reply_markup=None)

    # --- Monitoring Loop (Implemented in Phase 4) ---
    def _parse_price_from_condition(self, condition: str) -> float | None:
        match = re.search(r'[\d,]+\.?\d*', condition)
        if match:
            try:
                return float(match.group(0).replace(',', ''))
            except (ValueError, TypeError):
                return None
        return None

    async def _send_alert(self, report: AnalysisReport, message: str):
        chat_id = self.config.get('CHAT_ID')
        if chat_id:
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
        else:
            logger.warning(f"Cannot send alert for {report.pair}, CHAT_ID not configured.")

    async def _monitor_followed_analyses(self):
        logger.info("Starting analysis monitoring loop...")
        session_alerts = set()
        while True:
            await asyncio.sleep(10)
            if not self.bot_state["is_active"]:
                continue
            try:
                followed_analyses = self.tracker.get_followed_analyses()
                if not followed_analyses:
                    continue
                all_symbols = {analysis.pair for analysis in followed_analyses}
                price_data = {}
                for symbol in all_symbols:
                    okx_symbol = symbol.replace('/', '-')
                    cached_price = self.fetcher.get_cached_price(okx_symbol)
                    if cached_price and 'price' in cached_price:
                        price_data[symbol] = cached_price['price']
                for report in followed_analyses:
                    current_price = price_data.get(report.pair)
                    if not current_price:
                        continue
                    for tf_analysis in report.timeframe_analyses:
                        pattern = tf_analysis.pattern
                        if pattern.status == 'قيد التكوين':
                            activation_price = self._parse_price_from_condition(pattern.activation_condition)
                            invalidation_price = self._parse_price_from_condition(pattern.invalidation_condition)
                            if activation_price and current_price >= activation_price:
                                pattern.status = 'مفعل'
                                self.tracker.update_analysis(report)
                                alert_msg = f"🔔 <b>تنبيه تفعيل نموذج</b> 🔔\n<b>العملة:</b> {report.pair} (فريم {tf_analysis.timeframe})\n<b>السبب:</b> تم تفعيل نموذج <b>{pattern.name}</b> بوصول السعر إلى <b>{current_price}$</b> (شرط التفعيل: {activation_price}$)"
                                await self._send_alert(report, alert_msg)
                                continue
                            if invalidation_price and current_price <= invalidation_price:
                                pattern.status = 'فشل'
                                self.tracker.update_analysis(report)
                                alert_msg = f"🛑 <b>تنبيه فشل نموذج</b> 🛑\n<b>العملة:</b> {report.pair} (فريم {tf_analysis.timeframe})\n<b>السبب:</b> فشل نموذج <b>{pattern.name}</b> بكسر السعر لمستوى <b>{current_price}$</b> (شرط الإلغاء: {invalidation_price}$)"
                                await self._send_alert(report, alert_msg)
                                continue
                        for support in tf_analysis.supports:
                            alert_key = f"{report.report_id}:{tf_analysis.timeframe}:support:{support.level}"
                            if alert_key not in session_alerts and abs(current_price - support.level) / support.level < 0.005:
                                session_alerts.add(alert_key)
                                alert_msg = f"📉 <b>تنبيه دعم</b> 📉\n<b>العملة:</b> {report.pair} (فريم {tf_analysis.timeframe})\n<b>السبب:</b> السعر <b>{current_price}$</b> يقترب من منطقة دعم <b>{support.type}</b> عند <b>{support.level}$</b>"
                                await self._send_alert(report, alert_msg)
                        for resistance in tf_analysis.resistances:
                            alert_key = f"{report.report_id}:{tf_analysis.timeframe}:resistance:{resistance.level}"
                            if alert_key not in session_alerts and abs(current_price - resistance.level) / resistance.level < 0.005:
                                session_alerts.add(alert_key)
                                alert_msg = f"📈 <b>تنبيه مقاومة</b> 📈\n<b>العملة:</b> {report.pair} (فريم {tf_analysis.timeframe})\n<b>السبب:</b> السعر <b>{current_price}$</b> يقترب من منطقة مقاومة <b>{resistance.type}</b> عند <b>{resistance.level}$</b>"
                                await self._send_alert(report, alert_msg)
            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")

    # --- Bot Startup ---
    async def _post_init(self, application: Application):
        application.create_task(self._monitor_followed_analyses())

    def start(self):
        if not self.token:
            logger.error("CRITICAL: Telegram bot token not found.")
            return
        application = Application.builder().token(self.token).post_init(self._post_init).build()
        self.bot = application.bot
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))
        logger.info("🤖 Interactive bot and analysis monitor are starting...")
        application.run_polling()
