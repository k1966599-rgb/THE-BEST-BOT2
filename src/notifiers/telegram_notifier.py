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
from ..config import WATCHLIST, get_config
from ..utils.data_preprocessor import standardize_dataframe_columns
from ..decision_engine.trade_setup import TradeSetup


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
    def __init__(self, config: Dict, fetcher: BaseDataFetcher, orchestrator: AnalysisOrchestrator, decision_engine: DecisionEngine):
        super().__init__(config.get('telegram', {}))
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.decision_engine = decision_engine
        self.report_builder = ReportBuilder(config)
        self.bot_state = {"is_active": True}
        self.followed_trades: Dict[str, Dict[str, Any]] = {}
        self.last_analysis_results: Dict[int, List[Dict]] = {}
        self.token = self.config.get('BOT_TOKEN')
        self.bot = None

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
    def _get_analysis_timeframe_keyboard(self, symbol: str) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("تحليل طويل المدى", callback_data=f"analyze_long_{symbol}")],
                    [InlineKeyboardButton("تحليل متوسط المدى", callback_data=f"analyze_medium_{symbol}")],
                    [InlineKeyboardButton("تحليل قصير المدى", callback_data=f"analyze_short_{symbol}")],
                    [InlineKeyboardButton("🔙 رجوع لقائمة العملات", callback_data="analyze_menu")]]
        return InlineKeyboardMarkup(keyboard)

    def _get_follow_keyboard(self, trade_setup: TradeSetup) -> InlineKeyboardMarkup:
        symbol = trade_setup.symbol
        timeframe = trade_setup.timeframe
        keyboard = [[
            InlineKeyboardButton(f"📈 متابعة توصية {symbol}/{timeframe}", callback_data=f"follow_{symbol}_{timeframe}"),
            InlineKeyboardButton("🗑️ تجاهل", callback_data="ignore")
        ]]
        return InlineKeyboardMarkup(keyboard)

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    async def _run_analysis_for_request(self, symbol: str, timeframes: list, analysis_type: str) -> Dict[str, Any]:
        logger.info(f"Bot request: Starting analysis for {symbol} on timeframes: {timeframes}...")
        all_results = []
        for tf in timeframes:
            try:
                okx_symbol = symbol.replace('/', '-')
                api_timeframe = tf.replace('d', 'D').replace('h', 'H')
                historical_data_wrapper = await anyio.to_thread.run_sync(
                    self.fetcher.fetch_historical_data,
                    okx_symbol,
                    api_timeframe,
                    365
                )
                if not historical_data_wrapper or not historical_data_wrapper.get('data'):
                    raise ConnectionError(f"Failed to fetch data for {symbol} on {tf}")

                historical_data = historical_data_wrapper['data']
                df = pd.DataFrame(historical_data)
                df = standardize_dataframe_columns(df)
                df.set_index('timestamp', inplace=True)

                analysis_results = self.orchestrator.run(df)
                recommendation = self.decision_engine.make_recommendation(analysis_results, df, symbol, tf)
                all_results.append({'success': True, 'recommendation': recommendation})
            except Exception as e:
                logger.exception(f"Analysis failed for {symbol} on {tf} in bot request.")
                all_results.append({'success': False, 'timeframe': tf, 'error': str(e)})

        successful_recs = [r['recommendation'] for r in all_results if r.get('success')]
        if not successful_recs:
            return {'error': f"❌ تعذر تحليل {symbol} لجميع الأطر الزمنية المطلوبة."}

        ranked_recs = self.decision_engine.rank_recommendations(successful_recs)
        last_price_data = await anyio.to_thread.run_sync(self.fetcher.get_cached_price, symbol.replace('/', '-')) or {}

        general_info = {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'current_price': last_price_data.get('price', successful_recs[0].get('current_price', 0)),
            'timeframes': timeframes
        }
        return self.report_builder.build_report(ranked_results=ranked_recs, general_info=general_info)

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        MAX_LENGTH = 4096
        if len(text) <= MAX_LENGTH:
            await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return

        parts = []
        while len(text) > 0:
            if len(text) > MAX_LENGTH:
                part = text[:MAX_LENGTH]
                first_newline = part.rfind('\n')
                if first_newline != -1:
                    parts.append(part[:first_newline])
                    text = text[first_newline:]
                else:
                    parts.append(part)
                    text = text[MAX_LENGTH:]
            else:
                parts.append(text)
                break

        for part in parts:
            await self.bot.send_message(chat_id=chat_id, text=part, **kwargs)
            await asyncio.sleep(0.5)

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
            if not symbol or not timeframes:
                 await query.message.reply_text("خطأ: لم يتم تحديد العملة أو نوع التحليل بشكل صحيح.")
                 return
            await query.edit_message_text(text=f"جاري إعداد <b>{analysis_name}</b> لـ <code>{symbol}</code>...", parse_mode='HTML')
            try:
                report_parts = await self._run_analysis_for_request(symbol, timeframes, analysis_name)

                if 'error' in report_parts:
                    await query.message.reply_text(report_parts['error'])
                    return

                if report_parts.get("header"):
                    await self._send_long_message(chat_id=query.message.chat_id, text=report_parts["header"], parse_mode='HTML')

                for section in report_parts.get("timeframe_sections", []):
                    await self._send_long_message(chat_id=query.message.chat_id, text=section, parse_mode='HTML')
                    await asyncio.sleep(1)

                if report_parts.get("summary_and_recommendation"):
                    await self._send_long_message(chat_id=query.message.chat_id, text=report_parts["summary_and_recommendation"], parse_mode='HTML')

                ranked_results = report_parts.get('ranked_results', [])
                primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)

                if primary_rec and primary_rec.get('trade_setup'):
                    trade_setup = primary_rec['trade_setup']
                    self.last_analysis_results[query.message.chat_id] = trade_setup
                    await query.message.reply_text(text="هل تريد متابعة هذه التوصية النهائية؟", reply_markup=self._get_follow_keyboard(trade_setup))

            except Exception as e:
                logger.exception(f"Unhandled error in bot callback for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}", parse_mode='HTML')

        elif callback_data.startswith("follow_"):
            parts = callback_data.split("_")
            symbol = parts[1]
            timeframe = parts[2]
            chat_id = query.message.chat_id
            if chat_id in self.last_analysis_results:
                trade_setup = self.last_analysis_results[chat_id]
                if trade_setup and trade_setup.symbol == symbol and trade_setup.timeframe == timeframe:
                    self.followed_trades[f"{symbol}_{timeframe}"] = {"setup": trade_setup, "chat_id": chat_id}
                    await query.edit_message_text(text=f"✅ تمت إضافة {symbol} على فريم {timeframe} للمتابعة.")
                else:
                    await query.edit_message_text(text="❌ لم يتم العثور على الصفقة المحددة.")
            else:
                await query.edit_message_text(text="❌ انتهت صلاحية التحليل. يرجى طلب تحليل جديد.")

        elif callback_data == "ignore":
            await query.edit_message_text(text="تم تجاهل التحليل.")
            await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        logger.info("The `send` method is not implemented for the interactive bot. Use `start()` instead.")
        return False

    async def _send_trade_alert(self, trade_setup: TradeSetup, alert_type: str, chat_id: int):
        """
        Sends a trade alert to the user.
        """
        message = ""
        if alert_type == 'entry':
            message = f"🔔 تنبيه دخول: تم الوصول إلى سعر الدخول لـ {trade_setup.symbol} عند {trade_setup.entry_price:,.2f}"
        elif alert_type == 'stop_loss':
            message = f"🛑 تنبيه وقف الخسارة: تم الوصول إلى وقف الخسارة لـ {trade_setup.symbol} عند {trade_setup.stop_loss:,.2f}"
        elif alert_type == 'target1':
            message = f"🎯 تنبيه تحقيق الهدف الأول: تم الوصول إلى الهدف الأول لـ {trade_setup.symbol} عند {trade_setup.target1:,.2f}"
        elif alert_type == 'target2' and trade_setup.target2:
            message = f"🎯 تنبيه تحقيق الهدف الثاني: تم الوصول إلى الهدف الثاني لـ {trade_setup.symbol} عند {trade_setup.target2:,.2f}"

        if message:
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')

    async def _monitor_followed_trades(self):
        while True:
            await asyncio.sleep(10)
            for key, data in list(self.followed_trades.items()):
                trade_setup = data['setup']
                chat_id = data['chat_id']
                symbol = trade_setup.symbol.replace('/', '-')

                current_price_data = await anyio.to_thread.run_sync(self.fetcher.get_cached_price, symbol)
                if not current_price_data:
                    continue

                current_price = current_price_data.get('price', 0)

                if current_price >= trade_setup.entry_price:
                    await self._send_trade_alert(trade_setup, 'entry', chat_id)
                    del self.followed_trades[key]
                    continue

                if current_price <= trade_setup.stop_loss:
                    await self._send_trade_alert(trade_setup, 'stop_loss', chat_id)
                    del self.followed_trades[key]
                    continue

                if trade_setup.target1 and current_price >= trade_setup.target1:
                    await self._send_trade_alert(trade_setup, 'target1', chat_id)
                    if not trade_setup.target2:
                        del self.followed_trades[key]
                    else:
                        trade_setup.target1 = None
                    continue

                if trade_setup.target2 and current_price >= trade_setup.target2:
                    await self._send_trade_alert(trade_setup, 'target2', chat_id)
                    del self.followed_trades[key]
                    continue

    async def _post_init(self, application: Application):
        application.create_task(self._monitor_followed_trades())

    def start(self):
        if not self.token:
            logger.error("CRITICAL: Telegram bot token not found.")
            return

        application = Application.builder().token(self.token).post_init(self._post_init).build()
        self.bot = application.bot
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))

        logger.info("🤖 Interactive bot and trade monitor are starting...")
        application.run_polling()
