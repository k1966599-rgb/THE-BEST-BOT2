import asyncio
import logging
from typing import Dict, Any, List
import pandas as pd
import anyio
from ..data.base_fetcher import BaseDataFetcher
from ..analysis.orchestrator import AnalysisOrchestrator
from ..notifiers.telegram_sender import SimpleTelegramNotifier
from ..utils.data_preprocessor import standardize_dataframe_columns
from ..decision_engine.trade_setup import TradeSetup

logger = logging.getLogger(__name__)

class TradeMonitor:
    """Monitors active trade setups for key events, including complex confirmations."""
    def __init__(self, config: Dict, fetcher: BaseDataFetcher, orchestrator: AnalysisOrchestrator, notifier: SimpleTelegramNotifier):
        self.config = config
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.notifier = notifier
        self.active_trades: Dict[str, Dict] = {}
        self.pending_confirmation_trades: Dict[str, TradeSetup] = {}
        self.monitoring_interval_seconds = 60
        self.proximity_threshold = 0.0075

    def add_trade(self, initial_recommendation: Dict[str, Any]):
        trade_setup = initial_recommendation.get('trade_setup')
        if not trade_setup:
            logger.warning("Attempted to follow a trade without a trade_setup.")
            return

        key = f"{trade_setup.chat_id}_{trade_setup.symbol}_{trade_setup.timeframe}"

        if trade_setup.confirmation_rule == '3_candle_close':
            self.pending_confirmation_trades[key] = trade_setup
            logger.info(f"Trade added to PENDING CONFIRMATION: {key}")
            self.notifier.send(f"**تنبيه المراقبة: {trade_setup.symbol} ({trade_setup.timeframe})**\nتمت إضافة الصفقة للمراقبة. في انتظار اختراق السعر الأولي عند ${trade_setup.entry_price:,.2f} لبدء تأكيد الشموع.", trade_setup.chat_id)
        else:
            self.active_trades[key] = {
                "initial_recommendation": initial_recommendation,
                "chat_id": trade_setup.chat_id, "symbol": trade_setup.symbol,
                "timeframe": trade_setup.timeframe, "notified_events": set()
            }
            logger.info(f"Trade added to ACTIVE monitoring: {key}")

    async def run_monitoring_loop(self):
        logger.info("🚀 Trade monitoring loop started.")
        while True:
            try:
                await self._check_pending_confirmations()
                await self._check_active_trades()
            except Exception:
                logger.exception("Error in monitoring loop.")
            await asyncio.sleep(self.monitoring_interval_seconds)

    async def _check_pending_confirmations(self):
        if not self.pending_confirmation_trades:
            return

        logger.info(f"Checking {len(self.pending_confirmation_trades)} trades pending confirmation...")
        for key, trade in list(self.pending_confirmation_trades.items()):
            try:
                okx_symbol = trade.symbol.replace('/', '-')
                df_raw = await anyio.to_thread.run_sync(self.fetcher.fetch_historical_data, okx_symbol, trade.timeframe, 10)
                if not df_raw or not df_raw.get('data'): continue

                df = standardize_dataframe_columns(pd.DataFrame(df_raw['data']))
                if len(df) < 2: continue

                last_candle = df.iloc[-2]
                is_bullish = 'Bullish' in trade.pattern_name or 'Bottom' in trade.pattern_name

                if trade.confirmation_candles_closed == 0:
                    if (is_bullish and last_candle['close'] > trade.entry_price) or \
                       (not is_bullish and last_candle['close'] < trade.entry_price):
                        trade.confirmation_candles_closed = 1
                        logger.info(f"Initial breakout for {key}. Candle 1/3 confirmed.")
                        self.notifier.send(f"**تنبيه أولي: {trade.symbol} ({trade.timeframe})**\nتم اختراق السعر الأولي. بدء عد شموع التأكيد (1/3).", trade.chat_id)
                elif trade.confirmation_candles_closed > 0:
                    if (is_bullish and last_candle['close'] > trade.entry_price) or \
                       (not is_bullish and last_candle['close'] < trade.entry_price):
                        trade.confirmation_candles_closed += 1
                        logger.info(f"Consecutive close for {key}. Candle {trade.confirmation_candles_closed}/3 confirmed.")
                        self.notifier.send(f"**تأكيد المتابعة: {trade.symbol} ({trade.timeframe})**\nشمعة إضافية أغلقت في صالح الصفقة ({trade.confirmation_candles_closed}/3).", trade.chat_id)
                    else:
                        trade.confirmation_candles_closed = 0
                        logger.info(f"Confirmation failed for {key}. Resetting counter.")
                        self.notifier.send(f"**إعادة تعيين التأكيد: {trade.symbol} ({trade.timeframe})**\nفشلت شمعة في الحفاظ على الاختراق. تم إعادة تعيين عداد التأكيد.", trade.chat_id)

                if trade.confirmation_candles_closed >= 3:
                    logger.info(f"TRADE CONFIRMED for {key}. Moving to active monitoring.")
                    self.notifier.send(f"✅ **تم تأكيد الصفقة بالكامل: {trade.symbol} ({trade.timeframe})**\nتم إغلاق 3 شموع متتالية بنجاح. الصفقة الآن نشطة وتتم مراقبتها للأهداف ووقف الخسارة.", trade.chat_id)
                    initial_rec = {'trade_setup': trade, 'raw_analysis': trade.raw_pattern_data}
                    self.active_trades[key] = {
                        "initial_recommendation": initial_rec, "chat_id": trade.chat_id,
                        "symbol": trade.symbol, "timeframe": trade.timeframe, "notified_events": set()
                    }
                    del self.pending_confirmation_trades[key]
            except Exception as e:
                logger.exception(f"Error checking pending trade {key}: {e}")

    async def _check_active_trades(self):
        if not self.active_trades:
            return
        logger.info(f"Checking {len(self.active_trades)} active trades...")
        for key, trade_data in list(self.active_trades.items()):
            try:
                trade_setup = trade_data['initial_recommendation']['trade_setup']
                okx_symbol = trade_setup.symbol.replace('/', '-')
                latest_price_data = self.fetcher.get_cached_price(okx_symbol)
                if not latest_price_data: continue
                current_price = latest_price_data['price']
                await self._check_sl_tp_alerts(current_price, trade_data, key)
            except Exception as e:
                logger.exception(f"Error checking active trade {key}: {e}")

    async def _check_sl_tp_alerts(self, current_price: float, trade_data: Dict, trade_key: str):
        chat_id, symbol, notified_events = trade_data['chat_id'], trade_data['symbol'], trade_data['notified_events']
        trade_setup: TradeSetup = trade_data['initial_recommendation']['trade_setup']

        def notify(event_key: str, message: str):
            if event_key not in notified_events:
                self.notifier.send(f"**تنبيه صفقة نشطة: {symbol} ({trade_setup.timeframe})**\n{message}", chat_id)
                notified_events.add(event_key)

        if current_price < trade_setup.stop_loss:
            notify("stop_loss_hit", f"🛑 **تم ضرب وقف الخسارة!** تم الوصول إلى سعر وقف الخسارة ${trade_setup.stop_loss:,.2f}.")
            if self.active_trades.get(trade_key): del self.active_trades[trade_key]
            return

        if trade_setup.target2 and current_price >= trade_setup.target2:
             notify("target2_hit", f"🎯 **تم تحقيق الهدف الثاني!** تم الوصول إلى الهدف الثاني ${trade_setup.target2:,.2f}.")
             if self.active_trades.get(trade_key): del self.active_trades[trade_key]
             return
        elif current_price >= trade_setup.target1:
             notify("target1_hit", f"🎯 **تم تحقيق الهدف الأول!** تم الوصول إلى الهدف الأول ${trade_setup.target1:,.2f}.")
