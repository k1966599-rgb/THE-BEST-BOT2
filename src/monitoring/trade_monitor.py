import asyncio
import logging
from typing import Dict, Any, List
import pandas as pd
import anyio
from ..data.base_fetcher import BaseDataFetcher
from ..analysis.orchestrator import AnalysisOrchestrator
from ..notifiers.telegram_sender import SimpleTelegramNotifier
from ..utils.data_preprocessor import standardize_dataframe_columns

logger = logging.getLogger(__name__)

class TradeMonitor:
    """
    Monitors followed trades for specific events and sends alerts.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        fetcher: BaseDataFetcher,
        orchestrator: AnalysisOrchestrator,
        notifier: SimpleTelegramNotifier
    ):
        self.config = config
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.notifier = notifier
        self.followed_trades: Dict[str, Dict[str, Any]] = {}  # key: f"{chat_id}_{symbol}_{timeframe}"
        self.monitoring_interval_seconds = 60  # Check every 60 seconds

    def add_trade(self, initial_recommendation: Dict[str, Any]):
        """
        Adds a trade to the monitoring list.
        """
        trade_setup = initial_recommendation.get('trade_setup')
        if not trade_setup:
            logger.warning("Attempted to follow a trade with no setup details.")
            return

        chat_id = trade_setup.chat_id
        symbol = trade_setup.symbol
        timeframe = trade_setup.timeframe
        key = f"{chat_id}_{symbol}_{timeframe}"

        self.followed_trades[key] = {
            "initial_recommendation": initial_recommendation,
            "chat_id": chat_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "notified_events": set()  # To avoid sending duplicate alerts
        }
        logger.info(f"Added trade to monitor: {key}")

    async def run_monitoring_loop(self):
        """
        The main background task that periodically checks followed trades.
        """
        logger.info("🚀 Trade monitoring loop started.")
        while True:
            try:
                await self.check_all_trades()
            except Exception:
                logger.exception("An error occurred in the trade monitoring loop.")

            await asyncio.sleep(self.monitoring_interval_seconds)

    async def check_all_trades(self):
        """
        Iterates through all followed trades and checks for alert conditions.
        """
        if not self.followed_trades:
            return

        logger.info(f"Checking {len(self.followed_trades)} followed trades...")
        for key, trade_data in list(self.followed_trades.items()):
            try:
                symbol = trade_data['symbol']
                timeframe = trade_data['timeframe']
                okx_symbol = symbol.replace('/', '-')

                historical_data_wrapper = await anyio.to_thread.run_sync(self.fetcher.fetch_historical_data, okx_symbol, timeframe, 90)
                if not historical_data_wrapper or not historical_data_wrapper.get('data'):
                    logger.warning(f"Could not fetch historical data for {symbol} on {timeframe} for monitoring.")
                    continue

                df = pd.DataFrame(historical_data_wrapper['data'])
                df = standardize_dataframe_columns(df)

                latest_price_data = self.fetcher.get_cached_price(okx_symbol)
                if latest_price_data and not df.empty:
                    latest_price = latest_price_data['price']
                    df.loc[df.index[-1], 'close'] = latest_price
                    current_price = latest_price
                elif not df.empty:
                    current_price = df['close'].iloc[-1]
                else:
                    continue

                new_analysis_results = self.orchestrator.run(df.copy())

                await self._check_for_alerts(current_price, new_analysis_results, trade_data, key)

            except Exception as e:
                logger.exception(f"Error checking trade {key}: {e}")

    async def _check_for_alerts(self, current_price: float, new_analysis: Dict[str, Any], trade_data: Dict[str, Any], trade_key: str):
        """
        Compares new analysis with the initial one and generates alerts.
        """
        initial_rec = trade_data['initial_recommendation']
        initial_analysis = initial_rec.get('raw_analysis', {})
        chat_id = trade_data['chat_id']
        symbol = trade_data['symbol']
        notified_events = trade_data['notified_events']

        initial_supports = initial_analysis.get('supports', [])
        for support in initial_supports:
            level = support.value
            event_key = f"support_break_{level}"
            if current_price < level and event_key not in notified_events:
                message = f"🔔 تنبيه كسر دعم لـ {symbol}: السعر كسر مستوى الدعم ${level:,.2f} ({support.name})."
                self.notifier.send(message, chat_id)
                notified_events.add(event_key)

        initial_resistances = initial_analysis.get('resistances', [])
        for res in initial_resistances:
            level = res.value
            event_key = f"res_break_{level}"
            if current_price > level and event_key not in notified_events:
                message = f"🔔 تنبيه اختراق مقاومة لـ {symbol}: السعر اخترق مستوى المقاومة ${level:,.2f} ({res.name})."
                self.notifier.send(message, chat_id)
                notified_events.add(event_key)

        initial_pattern = initial_analysis.get('patterns', [])[0] if initial_analysis.get('patterns') else None
        new_pattern = new_analysis.get('patterns', [])[0] if new_analysis.get('patterns') else None

        if initial_pattern and new_pattern and initial_pattern.name == new_pattern.name:
            initial_status = initial_pattern.status
            new_status = new_pattern.status
            event_key = f"pattern_status_{new_status}"

            if new_status != initial_status and event_key not in notified_events:
                message = f"🔔 تنبيه تحديث نموذج لـ {symbol}: تغيرت حالة نموذج {initial_pattern.name} إلى '{new_status}'."
                self.notifier.send(message, chat_id)
                notified_events.add(event_key)

                if new_status in ['مفعل', 'فشل', 'ملغي']:
                    logger.info(f"Pattern for {trade_key} is terminal ('{new_status}'). Removing from monitor.")
                    del self.followed_trades[trade_key]
