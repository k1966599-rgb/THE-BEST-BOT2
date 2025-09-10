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

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Implementation of the abstract 'send' method.
        This bot is interactive, so this method is a placeholder.
        The main functionality is started via the `start()` method.
        """
        logger.warning(
            "The `send` method was called on the interactive bot, but it's not designed for direct sending. "
            "Use `start()` to run the bot."
        )
        return False

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
        """Restores the three analysis options (long, medium, short term)."""
        keyboard = [
            [InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
            [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
            [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
            [InlineKeyboardButton("🔙 رجوع لقائمة العملات", callback_data="analyze_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_follow_keyboard(self, report_id: str) -> InlineKeyboardMarkup:
        """Creates the new follow/ignore keyboard."""
        keyboard = [[
            InlineKeyboardButton("📈 متابعة", callback_data=f"follow:{report_id}"),
            InlineKeyboardButton("🗑️ تجاهل", callback_data=f"ignore:{report_id}")
        ]]
        return InlineKeyboardMarkup(keyboard)

    # --- Placeholder Analysis Generator (Updated) ---
    def _create_mock_analysis(self, pair: str, analysis_type: str, timeframes: List[str]) -> AnalysisReport:
        """
        Generates a mock analysis report that is now dynamic based on user selection.
        """
        report_id = str(uuid.uuid4())

        # Create a dynamic list of timeframe analyses
        timeframe_analyses = []
        for tf in timeframes:
            # Use generic mock data for each timeframe for demonstration
            analysis = TimeframeAnalysis(
                timeframe=tf, current_price=111550.0, # Price would be fetched live in a real scenario
                pattern=TechnicalPattern(name="نموذج قيد التحليل", status="قيد التكوين", activation_condition=f"اختراق المقاومة A", invalidation_condition=f"كسر الدعم B", target=12345.0),
                supports=[Support(type="دعم رئيسي", level=110000.0, strength="قوي")],
                resistances=[Resistance(type="مقاومة رئيسية", level=115000.0, strength="قوية")]
            )
            timeframe_analyses.append(analysis)

        # Create a generic summary
        summary_text = f"ملخص لـ {len(timeframes)} إطارات زمنية."
        summary = ExecutiveSummary(
            short_term_summary=summary_text,
            medium_term_summary=summary_text,
            long_term_summary=summary_text,
            critical_points={
                "resistance_breakout": "مراقبة اختراق المقاومات",
                "support_breakdown": "مراقبة كسر الدعوم"
            }
        )
        trade = ConfirmedTrade(
            entry_price_condition="عند تحقق شروط التفعيل",
            targets=[120000.0, 125000.0],
            stop_loss_condition="عند تحقق شروط الإلغاء",
            strategy_details="دمج الإشارات من جميع الإطارات الزمنية."
        )

        # Full Report
        return AnalysisReport(
            report_id=report_id,
            pair=pair,
            analysis_type=analysis_type, # Use the selected analysis type
            timeframe_analyses=timeframe_analyses,
            summary=summary,
            confirmed_trade=trade
        )

    # --- Core Logic (Refactored) ---
    async def _generate_and_send_new_analysis(self, chat_id: int, symbol: str, analysis_type: str, timeframes: List[str]):
        """Generates, saves, formats, and sends the new analysis report."""
        # 1. Generate the analysis (using the mock for now)
        report = self._create_mock_analysis(symbol, analysis_type, timeframes)

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

        # --- Analysis Trigger (Refactored for different scopes) ---
        elif callback_data.startswith("analyze_"):
            if not self.bot_state["is_active"]:
                await query.message.reply_text("البوت متوقف حاليًا. يرجى الضغط على 'تشغيل' أولاً.")
                return

            parts = callback_data.split("_")
            analysis_scope = parts[1]
            symbol = "_".join(parts[2:])

            # Get timeframe groups from config
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

            await query.edit_message_text(text=f"جاري إعداد *{analysis_type}* لـ `{symbol}`...", parse_mode=ParseMode.MARKDOWN_V2)
            try:
                # Pass the correct parameters to the analysis function
                await self._generate_and_send_new_analysis(
                    chat_id=query.message.chat_id,
                    symbol=symbol,
                    analysis_type=analysis_type,
                    timeframes=timeframes
                )
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
