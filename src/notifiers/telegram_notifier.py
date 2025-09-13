import logging
import re
import time
import anyio
import asyncio
from typing import Dict, Any, List
import pandas as pd

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from .base_notifier import BaseNotifier
from ..data.base_fetcher import BaseDataFetcher
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
    """The main interactive Telegram bot class.

    This class orchestrates the bot's functionality, including handling user
    commands, presenting menus, running analysis on demand, and interacting
    with the TradeMonitor to follow promising trade setups.
    """
    def __init__(self, config: Dict, fetcher: BaseDataFetcher, orchestrator: AnalysisOrchestrator, decision_engine: DecisionEngine):
        """Initializes the InteractiveTelegramBot.

        Args:
            config (Dict): The full application configuration.
            fetcher (BaseDataFetcher): An instance of the data fetcher.
            orchestrator (AnalysisOrchestrator): An instance of the analysis
                orchestrator.
            decision_engine (DecisionEngine): An instance of the decision engine.
        """
        self.full_config = config
        super().__init__(config.get('telegram', {}))
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.decision_engine = decision_engine
        self.report_builder = ReportBuilder(config)
        self.bot_state = {"is_active": True}
        self.last_analysis_results: Dict[int, List[Dict]] = {}
        self.token = self.config.get('BOT_TOKEN')
        self.bot = None

        alert_notifier = SimpleTelegramNotifier(config.get('telegram', {}))
        self.trade_monitor = TradeMonitor(
            config=config,
            fetcher=fetcher,
            orchestrator=orchestrator,
            notifier=alert_notifier
        )

    def _get_start_message_text(self) -> str:
        """Generates the text for the main start message."""
        status = "🟢 متصل وجاهز" if self.bot_state["is_active"] else "🔴 متوقف"
        return f"💎 <b>أفضل بوت</b> 💎\n<b>حالة النظام:</b> {status}"

    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        """Generates the main menu inline keyboard."""
        keyboard = [[InlineKeyboardButton("▶️ بدء", callback_data="start_bot"), InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_bot")],
                    [InlineKeyboardButton("🔍 تحليل", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_coin_list_keyboard(self) -> InlineKeyboardMarkup:
        """Generates the keyboard for selecting a coin from the watchlist."""
        watchlist = self.full_config.get('trading', {}).get('WATCHLIST', [])
        keyboard = [[InlineKeyboardButton(coin, callback_data=f"coin_{coin}") for coin in watchlist[i:i+2]] for i in range(0, len(watchlist), 2)]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")])
        return InlineKeyboardMarkup(keyboard)

    def _get_analysis_timeframe_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        """Generates the keyboard for selecting an analysis type for a symbol.

        Args:
            symbol (str): The symbol for which to generate the keyboard.

        Returns:
            InlineKeyboardMarkup: The generated keyboard.
        """
        keyboard = [[InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
                    [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
                    [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
                    [InlineKeyboardButton("🔙 رجوع إلى قائمة العملات", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_follow_keyboard(self, trade_setup: TradeSetup) -> InlineKeyboardMarkup:
        """Generates the keyboard to ask the user if they want to follow a trade.

        Args:
            trade_setup (TradeSetup): The trade setup object.

        Returns:
            InlineKeyboardMarkup: The generated keyboard.
        """
        symbol = trade_setup.symbol
        timeframe = trade_setup.timeframe
        keyboard = [[
            InlineKeyboardButton(f"📈 متابعة توصية {symbol}/{timeframe}", callback_data=f"follow_{symbol}_{timeframe}"),
            InlineKeyboardButton("🗑️ تجاهل", callback_data="ignore")
        ]]
        return InlineKeyboardMarkup(keyboard)

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the /start command, sending the main menu."""
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    async def _run_analysis_for_request(self, chat_id: int, symbol: str, timeframes: list, analysis_type: str) -> Dict[str, Any]:
        """Runs the full analysis pipeline for a user request.

        This method fetches data, runs the orchestrator and decision engine
        for multiple timeframes, then builds a comprehensive report.

        Args:
            chat_id (int): The user's chat ID.
            symbol (str): The symbol to analyze.
            timeframes (list): A list of timeframes to analyze.
            analysis_type (str): The user-facing name for the analysis type.

        Returns:
            Dict[str, Any]: A dictionary containing the report parts, or an
            error message.
        """
        logger.info(f"طلب بوت: بدء التحليل لـ {symbol} على الأطر الزمنية: {timeframes}...")
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
                    raise ConnectionError(f"فشل في جلب البيانات لـ {symbol} على {tf}")

                historical_data = historical_data_wrapper['data']
                df = pd.DataFrame(historical_data)
                df = standardize_dataframe_columns(df)
                df.set_index('timestamp', inplace=True)

                if not df.empty:
                    current_price = df['close'].iloc[-1]

                analysis_results = self.orchestrator.run(df)
                recommendation = self.decision_engine.make_recommendation(analysis_results, df, symbol, tf, chat_id)
                recommendation['current_price'] = current_price
                all_results.append(recommendation)
            except ConnectionError as e:
                logger.error(f"خطأ في الاتصال أثناء التحليل لـ {symbol} على {tf}: {e}")
            except (ValueError, KeyError) as e:
                logger.error(f"خطأ في معالجة البيانات لـ {symbol} على {tf}: {e}")
            except Exception as e:
                logger.exception(f"خطأ غير معالج أثناء التحليل لـ {symbol} في طلب البوت.")

        if not all_results:
            return {'error': f"❌ تعذر تحليل {symbol} لجميع الأطر الزمنية المطلوبة."}

        ranked_recs = self.decision_engine.rank_recommendations(all_results)

        general_info = {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'current_price': current_price,
            'timeframes': timeframes
        }
        return self.report_builder.build_report(ranked_results=ranked_recs, general_info=general_info)

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        """Sends a message, splitting it into multiple parts if it's too long.

        Args:
            chat_id: The ID of the chat to send the message to.
            text (str): The message text.
            **kwargs: Additional keyword arguments for `send_message`.
        """
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
        """The central callback handler for all inline keyboard buttons.

        This method acts as a router, dispatching actions based on the
        `callback_data` received from the user's button press. It handles
        everything from navigating menus to triggering analysis and following
        trades.
        """
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
                await query.message.reply_text("البوت متوقف حاليًا. يرجى الضغط على 'بدء' أولاً.")
                return
            await query.edit_message_text(text="الرجاء اختيار عملة لتحليلها:", reply_markup=self._get_coin_list_keyboard())
        elif callback_data.startswith("coin_"):
            symbol = callback_data.split("_", 1)[1]
            await query.edit_message_text(text=f"اختر نوع التحليل لـ <code>{symbol}</code>:", reply_markup=self._get_analysis_timeframe_keyboard(symbol), parse_mode='HTML')
        elif callback_data.startswith("analyze_"):
            parts = callback_data.split("_")
            analysis_scope = parts[1]
            symbol = "_".join(parts[2:])
            analysis_map = {
                "long": ("استثمار طويل المدى", self.full_config['trading']['TIMEFRAME_GROUPS']['long_term']),
                "medium": ("تداول متوسط المدى", self.full_config['trading']['TIMEFRAME_GROUPS']['medium_term']),
                "short": ("مضاربة سريعة", self.full_config['trading']['TIMEFRAME_GROUPS']['short_term'])
            }
            analysis_name, timeframes = analysis_map.get(analysis_scope, ("غير محدد", []))
            if not symbol or not timeframes:
                 await query.message.reply_text("خطأ: لم يتم تحديد العملة أو نوع التحليل بشكل صحيح.")
                 return

            await query.edit_message_text(text=f"جاري تحضير <b>{analysis_name}</b> لـ <code>{symbol}</code>...", parse_mode='HTML')
            try:
                chat_id = query.message.chat_id
                # This now returns a list of message dicts, or a dict with an error key.
                report_messages = await self._run_analysis_for_request(chat_id, symbol, timeframes, analysis_name)

                # Check for an error dictionary before proceeding
                if isinstance(report_messages, dict) and 'error' in report_messages:
                    await query.message.reply_text(report_messages['error'])
                    return

                # The result is a list of messages, handle it sequentially.
                if isinstance(report_messages, list):
                    # Save the analysis results for the follow/ignore feature
                    if report_messages:
                        # The ranked_results are attached to each message dict by the builder
                        self.last_analysis_results[chat_id] = report_messages[0].get('ranked_results', [])

                    # Sequentially send each message
                    for message_info in report_messages:
                        content = message_info.get("content")
                        # The builder does not yet support keyboards, so this is placeholder logic
                        # for when it is added. For now, it correctly sends the content.
                        reply_markup = None

                        if content:
                            await self._send_long_message(
                                chat_id=chat_id,
                                text=content,
                                parse_mode='HTML',
                                reply_markup=reply_markup
                            )

                    # After sending all parts, show the follow/ignore keyboard if applicable
                    primary_rec = next((r for r in self.last_analysis_results.get(chat_id, []) if r.get('trade_setup')), None)
                    if primary_rec:
                        await query.message.reply_text(text="هل تريد متابعة هذه التوصية النهائية؟", reply_markup=self._get_follow_keyboard(primary_rec['trade_setup']))
                    else:
                        await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

            except Exception as e:
                logger.exception(f"خطأ غير معالج في رد البوت لـ {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}", parse_mode='HTML')

        elif callback_data.startswith("follow_"):
            chat_id = query.message.chat_id
            if chat_id in self.last_analysis_results:
                ranked_results = self.last_analysis_results[chat_id]
                primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
                if primary_rec:
                    self.trade_monitor.add_trade(primary_rec)
                    symbol = primary_rec.get('symbol')
                    timeframe = primary_rec.get('timeframe')
                    await query.edit_message_text(text=f"✅ تمت إضافة {symbol} على الإطار الزمني {timeframe} للمراقبة.")
                    await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
                else:
                    await query.edit_message_text(text="❌ تعذر العثور على الصفقة المحددة.")
                    await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')
            else:
                await query.edit_message_text(text="❌ انتهت صلاحية التحليل. يرجى طلب تحليل جديد.")
                await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

        elif callback_data == "ignore":
            await query.edit_message_text(text="تم تجاهل التحليل.")
            await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Not implemented for the interactive bot. Use `start()`."""
        logger.info("The `send` method is not implemented for the interactive bot. Use `start()` instead.")
        return False

    async def _post_init(self, application: Application):
        """A coroutine to be run after the application is built.

        This method links the application's bot instance to the trade
        monitor's notifier and starts the monitoring loop as a background task.

        Args:
            application (Application): The `python-telegram-bot` Application.
        """
        self.trade_monitor.notifier.bot = application.bot
        application.create_task(self.trade_monitor.run_monitoring_loop())

    def start(self):
        """Starts the interactive Telegram bot.

        This method sets up the `python-telegram-bot` application, adds the
        necessary handlers, and starts the polling loop to receive updates.
        """
        if not self.token:
            logger.error("خطأ فادح: لم يتم العثور على توكن بوت التليجرام.")
            return

        application = Application.builder().token(self.token).post_init(self._post_init).build()
        self.bot = application.bot
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))

        logger.info("🤖 يتم بدء البوت التفاعلي ومراقب الصفقات...")
        application.run_polling()
