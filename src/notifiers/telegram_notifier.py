import logging
import re
import time
import asyncio
from typing import Dict, Any
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
        self.token = self.config.get('BOT_TOKEN')

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

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    async def _run_analysis_for_request(self, symbol: str, timeframes: list, analysis_type: str) -> str:
        # This function remains the same as the previous correct version
        logger.info(f"Bot request: Starting analysis for {symbol} on timeframes: {timeframes}...")
        all_results = []
        for tf in timeframes:
            try:
                okx_symbol = symbol.replace('/', '-')
                api_timeframe = tf.replace('d', 'D').replace('h', 'H')
                historical_data = await asyncio.to_thread(
                    self.fetcher.fetch_historical_data,
                    symbol=okx_symbol, timeframe=api_timeframe, days_to_fetch=365
                )
                if not historical_data:
                    raise ConnectionError(f"Failed to fetch data for {symbol} on {tf}")
                df = pd.DataFrame(historical_data)
                df = standardize_dataframe_columns(df)
                df.set_index('timestamp', inplace=True)
                analysis_results = self.orchestrator.run(df)
                recommendation = self.decision_engine.make_recommendation(analysis_results, df, symbol, tf)
                recommendation['timeframe'] = tf
                recommendation['symbol'] = symbol
                recommendation['current_price'] = df['close'].iloc[-1] # Keep this for the header price
                all_results.append({'success': True, 'recommendation': recommendation})
            except Exception as e:
                logger.exception(f"Analysis failed for {symbol} on {tf} in bot request.")
                all_results.append({'success': False, 'timeframe': tf, 'error': str(e)})
        successful_recs = [r['recommendation'] for r in all_results if r.get('success')]
        if not successful_recs:
            return f"❌ تعذر تحليل {symbol} لجميع الأطر الزمنية المطلوبة."
        ranked_recs = self.decision_engine.rank_recommendations(successful_recs)
        last_price_data = await asyncio.to_thread(self.fetcher.get_cached_price, symbol.replace('/', '-')) or {}
        general_info = {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'current_price': last_price_data.get('price', successful_recs[0].get('current_price', 0)),
            'timeframes': timeframes
        }
        return self.report_builder.build_report(ranked_results=ranked_recs, general_info=general_info)

    async def _send_long_message(self, chat_id, text: str, **kwargs):
        """
        Splits a long message into multiple messages if it exceeds Telegram's limit.
        """
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
            await asyncio.sleep(0.5) # Small delay to avoid rate limiting

    async def _main_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        callback_data = query.data
        logger.info(f"DEBUG: Received callback_data: '{callback_data}'")

        # THIS IS THE CORRECTED LOGIC BLOCK
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

                # Send the report in parts
                if report_parts.get("header"):
                    await self._send_long_message(chat_id=query.message.chat_id, text=report_parts["header"], parse_mode='HTML')

                for section in report_parts.get("timeframe_sections", []):
                    await self._send_long_message(chat_id=query.message.chat_id, text=section, parse_mode='HTML')
                    await asyncio.sleep(1) # Delay between timeframe messages

                if report_parts.get("summary_and_recommendation"):
                    await self._send_long_message(chat_id=query.message.chat_id, text=report_parts["summary_and_recommendation"], parse_mode='HTML')

            except Exception as e:
                logger.exception(f"Unhandled error in bot callback for {symbol}.")
                await query.message.reply_text(f"حدث خطأ فادح: {e}", parse_mode='HTML')
            finally:
                await query.message.reply_text(text=self._get_start_message_text(), reply_markup=self._get_main_keyboard(), parse_mode='HTML')

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        logger.info("The `send` method is not implemented for the interactive bot. Use `start()` instead.")
        return False

    def start(self):
        if not self.token:
            logger.error("CRITICAL: Telegram bot token not found.")
            return
        application = Application.builder().token(self.token).build()
        self.bot = application.bot
        application.add_handler(CommandHandler("start", self._start_command))
        application.add_handler(CallbackQueryHandler(self._main_button_callback))
        logger.info("🤖 Interactive bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
