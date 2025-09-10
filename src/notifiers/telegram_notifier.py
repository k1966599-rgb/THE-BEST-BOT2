import logging
import re
import asyncio
import uuid
from typing import Dict, Any
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
        # Use the new AnalysisTracker
        self.tracker = AnalysisTracker()

    # --- Keyboard Layouts (Refactored) ---
    def _get_start_message_text(self) -> str:
        status = "🟢 متصل وجاهز للعمل" if self.bot_state["is_active"] else "🔴 متوقف"
        return f"💎 *THE BEST BOT* 💎\n*حالة النظام:* {status}"

    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("▶️ تشغيل", callback_data="start_bot"), InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
                    [InlineKeyboardButton("🔍 تحليل", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_coin_list_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton(coin, callback_data=f"coin_{coin}") for coin in WATCHLIST[i:i+2]] for i in range(0, len(WATCHLIST), 2)]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")])
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_type_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        # Simplified for now, as the new structure is more generic
        keyboard = [[InlineKeyboardButton("تحليل شامل", callback_data=f"analyze_full_{symbol}")],
                    [InlineKeyboardButton("🔙 رجوع لقائمة العملات", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_follow_keyboard(self, report_id: str) -> InlineKeyboardMarkup:
        """Creates the new follow/ignore keyboard."""
        keyboard = [[
            InlineKeyboardButton("📈 متابعة", callback_data=f"follow:{report_id}"),
            InlineKeyboardButton("🗑️ تجاهل", callback_data=f"ignore:{report_id}")
        ]]
        return InlineKeyboardMarkup(keyboard)

    # --- Placeholder Analysis Generator ---
    def _create_mock_analysis(self, pair: str) -> AnalysisReport:
        """
        Generates a hardcoded mock analysis report based on the user's BTC/USDT example.
        This is a placeholder for the real analysis logic.
        """
        report_id = str(uuid.uuid4())
        # Data for 1H
        h1_analysis = TimeframeAnalysis(
            timeframe="1H", current_price=111550.0,
            pattern=TechnicalPattern(name="مثلث صاعد", status="قيد التكوين", activation_condition="اختراق المقاومة 112,000$ مع ثبات شمعة ساعة فوقها", invalidation_condition="كسر الدعم 110,530$ مع إغلاق شمعة ساعة تحته", target=115500.0),
            supports=[Support(type="دعم ترند قصير", level=110530.0, strength="حرج"), Support(type="دعم فيبو 0.618", level=110920.0, strength="قوي")],
            resistances=[Resistance(type="مقاومة رئيسية", level=112000.0, strength="حرجة"), Resistance(type="مقاومة هدف النموذج", level=115500.0, strength="فني")]
        )
        # Data for 4H
        h4_analysis = TimeframeAnalysis(
            timeframe="4H", current_price=111550.0,
            pattern=TechnicalPattern(name="علم صاعد", status="مفعل", activation_condition="اختراق المقاومة 114,000$ مع إغلاق شمعة 4 ساعات فوقها", invalidation_condition="كسر الدعم 111,000$ مع إغلاق شمعة 4 ساعات تحته", target=117000.0),
            supports=[Support(type="دعم ترند متوسط", level=111000.0, strength="حرج"), Support(type="دعم قناة/قاع العلم", level=111500.0, strength="قوي")],
            resistances=[Resistance(type="مقاومة العلم", level=114000.0, strength="حرجة"), Resistance(type="مقاومة هدف النموذج", level=117000.0, strength="فني")]
        )
        # Data for 1D
        d1_analysis = TimeframeAnalysis(
            timeframe="1D", current_price=111550.0,
            pattern=TechnicalPattern(name="قاع مزدوج", status="فشل", activation_condition="اختراق خط العنق 123,226$ مع إغلاق شمعة يومية فوقه", invalidation_condition="كسر القاع الثاني 98,924$ مع إغلاق شمعة يومية تحته", target=147000.0),
            supports=[Support(type="دعم ترند طويل", level=98924.0, strength="حرج"), Support(type="دعم فيبو 0.5", level=110800.0, strength="متوسط")],
            resistances=[Resistance(type="خط عنق القاع المزدوج", level=123226.0, strength="حرجة"), Resistance(type="مقاومة هدف النموذج", level=147000.0, strength="فني")]
        )
        # Summary and Trade
        summary = ExecutiveSummary(
            short_term_summary="مثلث صاعد → اختراق 112,000$ → أهداف: 115,500$ → 117,500$",
            medium_term_summary="علم صاعد → اختراق 114,000$ → أهداف: 117,000$ → 118,300$",
            long_term_summary="قاع مزدوج → اختراق 123,226$ → أهداف: 135,000$ → 147,000$",
            critical_points={
                "resistance_breakout": "اختراق المقاومة: 1H = 112,000$, 4H = 114,000$, 1D = 123,226$",
                "support_breakdown": "كسر الدعم: 1H = 110,530$, 4H = 111,000$, 1D = 98,924$"
            }
        )
        trade = ConfirmedTrade(
            entry_price_condition="عند اختراق 112,000$ (فريم 1H) مع ثبات السعر فوق المقاومة 3 شموع ساعة متتالية",
            targets=[115500.0, 117500.0, 120000.0],
            stop_loss_condition="عند كسر 110,530$ (فريم 1H)",
            strategy_details="متابعة فريم 4H لاختراق 114,000$ → أهداف 117,000$ – 118,300$"
        )
        # Full Report
        return AnalysisReport(
            report_id=report_id, pair=pair, timeframe_analyses=[h1_analysis, h4_analysis, d1_analysis],
            summary=summary, confirmed_trade=trade
        )

    # --- Core Logic (Refactored) ---
    async def _generate_and_send_new_analysis(self, chat_id: int, symbol: str):
        """Generates, saves, formats, and sends the new analysis report."""
        # 1. Generate the analysis (using the mock for now)
        report = self._create_mock_analysis(symbol)

        # 2. Save the report to the tracker with is_followed=False
        # This ensures we have a record and an ID to reference in the buttons
        self.tracker.follow_analysis(report) # follow_analysis now handles both add and update
        self.tracker.unfollow_analysis(report.report_id) # Immediately set to not followed

        # 3. Format messages
        formatted_messages = format_full_analysis_messages(report)
        timeframe_msgs = formatted_messages["timeframe_messages"]
        summary_msg = formatted_messages["summary_message"]

        # 4. Send timeframe messages
        for msg in timeframe_msgs:
            await self._send_long_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN_V2)
            await asyncio.sleep(0.5) # Small delay between messages

        # 5. Send summary message with follow/ignore buttons
        keyboard = self._get_analysis_follow_keyboard(report.report_id)
        await self._send_long_message(chat_id, summary_msg, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        """Sends a message, splitting it if it exceeds Telegram's character limit."""
        MAX_LENGTH = 4096
        # Telegram's MarkdownV2 requires escaping certain characters.
        # A simple replacement strategy is used here.
        escaped_text = text.replace('.', '\\.').replace('-', '\\-').replace('$', '\\$').replace('(', '\\(').replace(')', '\\)').replace('!', '\\!')

        if len(escaped_text) <= MAX_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=escaped_text, **kwargs)
            return

        parts = []
        # Basic splitting logic, can be improved
        for i in range(0, len(escaped_text), MAX_LENGTH):
            parts.append(escaped_text[i:i + MAX_LENGTH])

        for part in parts:
            await self.bot.send_message(chat_id=chat_id, text=part, **kwargs)
            await asyncio.sleep(0.5)

    # --- Command and Callback Handlers (Refactored) ---
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)

    async def _main_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data

        # --- Menu Navigation ---
        if callback_data == "start_menu":
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        elif callback_data == "start_bot":
            self.bot_state["is_active"] = True
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        elif callback_data == "stop_bot":
            self.bot_state["is_active"] = False
            await query.edit_message_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        elif callback_data == "analyze_menu":
            await query.edit_message_text(text="الرجاء اختيار عملة للتحليل:", reply_markup=self._get_coin_list_keyboard())
        elif callback_data.startswith("coin_"):
            symbol = callback_data.split("_", 1)[1]
            await query.edit_message_text(text=f"اختر نوع التحليل لـ `{symbol}`:", reply_markup=self._get_analysis_type_keyboard(symbol), parse_mode=ParseMode.MARKDOWN_V2)

        # --- Analysis Trigger (Refactored) ---
        elif callback_data.startswith("analyze_full_"):
            if not self.bot_state["is_active"]:
                await query.message.reply_text("البوت متوقف حاليًا. يرجى الضغط على 'تشغيل' أولاً.")
                return
            symbol = callback_data.replace("analyze_full_", "")
            await query.edit_message_text(text=f"جاري إعداد تحليل شامل لـ `{symbol}`...", parse_mode=ParseMode.MARKDOWN_V2)
            try:
                await self._generate_and_send_new_analysis(query.message.chat_id, symbol)
            except Exception as e:
                logger.exception(f"Error generating new analysis for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}")

        # --- Follow/Ignore Callbacks (New) ---
        elif callback_data.startswith("follow:"):
            report_id = callback_data.split(":", 1)[1]
            report = self.tracker.get_analysis_by_id(report_id)
            if report:
                report.is_followed = True
                self.tracker.update_analysis(report)
                await query.edit_message_text(text=f"✅ *تمت إضافة تحليل {report.pair} للمتابعة اللحظية.*", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=None)
            else:
                await query.edit_message_text(text="❌ لم يتم العثور على التحليل. ربما انتهت صلاحيته.", reply_markup=None)

        elif callback_data.startswith("ignore:"):
            report_id = callback_data.split(":", 1)[1]
            self.tracker.unfollow_analysis(report_id) # This just sets the flag to false
            await query.edit_message_text(text="*تم تجاهل التحليل.*", parse_mode=ParseMode.MARKDOWN_V2, reply_markup=None)

    # --- Monitoring Loop (Implemented in Phase 4) ---
    def _parse_price_from_condition(self, condition: str) -> float | None:
        """Extracts the first floating-point number from a condition string."""
        # This regex finds numbers that may include commas and a decimal point
        match = re.search(r'[\d,]+\.?\d*', condition)
        if match:
            try:
                # Remove commas before converting to float
                return float(match.group(0).replace(',', ''))
            except (ValueError, TypeError):
                return None
        return None

    async def _send_alert(self, report: AnalysisReport, message: str):
        """Helper to send alerts. Assumes a 'chat_id' could be stored with a report if needed."""
        # For now, we need a way to get the chat_id. Let's assume we store it.
        # This part is a simplification. A real bot might need a user management system.
        # For now, I will assume a single user and get chat_id from config.
        chat_id = self.config.get('CHAT_ID')
        if chat_id:
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            logger.warning(f"Cannot send alert for {report.pair}, CHAT_ID not configured.")


    async def _monitor_followed_analyses(self):
        """The new monitoring loop that checks prices and sends alerts."""
        logger.info("Starting analysis monitoring loop...")
        # A set to track alerts sent in this session to avoid spam for S/R levels.
        session_alerts = set()

        while True:
            await asyncio.sleep(10) # Check every 10 seconds
            if not self.bot_state["is_active"]:
                continue

            try:
                followed_analyses = self.tracker.get_followed_analyses()
                if not followed_analyses:
                    continue

                # 1. Get all unique symbols and fetch their prices
                all_symbols = {analysis.pair for analysis in followed_analyses}
                price_data = {}
                for symbol in all_symbols:
                    okx_symbol = symbol.replace('/', '-')
                    cached_price = self.fetcher.get_cached_price(okx_symbol)
                    if cached_price and 'price' in cached_price:
                        price_data[symbol] = cached_price['price']

                # 2. Iterate through analyses and check conditions
                for report in followed_analyses:
                    current_price = price_data.get(report.pair)
                    if not current_price:
                        continue

                    for tf_analysis in report.timeframe_analyses:
                        pattern = tf_analysis.pattern

                        # Check for pattern status changes (only if 'in formation')
                        if pattern.status == 'قيد التكوين':
                            activation_price = self._parse_price_from_condition(pattern.activation_condition)
                            invalidation_price = self._parse_price_from_condition(pattern.invalidation_condition)

                            # Check for activation
                            if activation_price and current_price >= activation_price:
                                pattern.status = 'مفعل'
                                self.tracker.update_analysis(report)
                                alert_msg = f"🔔 *تنبيه تفعيل نموذج* 🔔\n*العملة:* {report.pair} (فريم {tf_analysis.timeframe})\n*السبب:* تم تفعيل نموذج *{pattern.name}* بوصول السعر إلى *{current_price}$* (شرط التفعيل: {activation_price}$)"
                                await self._send_alert(report, alert_msg)
                                continue # Move to next timeframe analysis

                            # Check for invalidation
                            if invalidation_price and current_price <= invalidation_price:
                                pattern.status = 'فشل'
                                self.tracker.update_analysis(report)
                                alert_msg = f"🛑 *تنبيه فشل نموذج* 🛑\n*العملة:* {report.pair} (فريم {tf_analysis.timeframe})\n*السبب:* فشل نموذج *{pattern.name}* بكسر السعر لمستوى *{current_price}$* (شرط الإلغاء: {invalidation_price}$)"
                                await self._send_alert(report, alert_msg)
                                continue

                        # Check for Support/Resistance proximity alerts
                        for support in tf_analysis.supports:
                            alert_key = f"{report.report_id}:{tf_analysis.timeframe}:support:{support.level}"
                            if alert_key not in session_alerts and abs(current_price - support.level) / support.level < 0.005: # 0.5% proximity
                                session_alerts.add(alert_key)
                                alert_msg = f"📉 *تنبيه دعم* 📉\n*العملة:* {report.pair} (فريم {tf_analysis.timeframe})\n*السبب:* السعر *{current_price}$* يقترب من منطقة دعم *{support.type}* عند *{support.level}$*"
                                await self._send_alert(report, alert_msg)

                        for resistance in tf_analysis.resistances:
                            alert_key = f"{report.report_id}:{tf_analysis.timeframe}:resistance:{resistance.level}"
                            if alert_key not in session_alerts and abs(current_price - resistance.level) / resistance.level < 0.005: # 0.5% proximity
                                session_alerts.add(alert_key)
                                alert_msg = f"📈 *تنبيه مقاومة* 📈\n*العملة:* {report.pair} (فريم {tf_analysis.timeframe})\n*السبب:* السعر *{current_price}$* يقترب من منطقة مقاومة *{resistance.type}* عند *{resistance.level}$*"
                                await self._send_alert(report, alert_msg)

            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")

    # --- Bot Startup ---
    async def _post_init(self, application: Application):
        """Runs after the application is initialized."""
        application.create_task(self._monitor_followed_analyses())

    def start(self):
        """Starts the Telegram bot polling."""
        if not self.token:
            logger.error("CRITICAL: Telegram bot token not found.")
            return

        application = Application.builder().token(self.token).post_init(self._post_init).build()
        self.bot = application.bot

        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))

        logger.info("🤖 Interactive bot and analysis monitor are starting...")
        application.run_polling()
