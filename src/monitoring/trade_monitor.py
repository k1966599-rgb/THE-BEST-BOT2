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
    """Monitors active trade setups for key events and sends alerts.

    This class runs a continuous background loop to check followed trades
    against new market data. It can detect events like price approaching key
    levels, stop-loss hits, target achievements, and pattern status changes,
    sending notifications via the provided notifier.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        fetcher: BaseDataFetcher,
        orchestrator: AnalysisOrchestrator,
        notifier: SimpleTelegramNotifier
    ):
        """Initializes the TradeMonitor.

        Args:
            config (Dict[str, Any]): The main configuration dictionary.
            fetcher (BaseDataFetcher): An instance of a data fetcher to get
                updated market data.
            orchestrator (AnalysisOrchestrator): An instance of the analysis
                orchestrator to re-evaluate the market state.
            notifier (SimpleTelegramNotifier): An instance of a notifier to
                send alerts.
        """
        self.config = config
        self.fetcher = fetcher
        self.orchestrator = orchestrator
        self.notifier = notifier
        self.followed_trades: Dict[str, Dict[str, Any]] = {}  # key: f"{chat_id}_{symbol}_{timeframe}"
        self.monitoring_interval_seconds = 60  # Check every 60 seconds
        self.proximity_threshold = 0.0075 # 0.75% proximity to be considered "approaching"

    def add_trade(self, initial_recommendation: Dict[str, Any]):
        """Adds a trade setup to the monitoring list.

        Args:
            initial_recommendation (Dict[str, Any]): The initial recommendation
                dictionary which must contain a 'trade_setup' object.
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
        """The main background task that periodically checks followed trades.

        This method runs an infinite loop that calls `check_all_trades` at a
        regular interval defined by `monitoring_interval_seconds`.
        """
        logger.info("🚀 Trade monitoring loop started.")
        while True:
            try:
                await self.check_all_trades()
            except Exception:
                logger.exception("An error occurred in the trade monitoring loop.")

            await asyncio.sleep(self.monitoring_interval_seconds)

    async def check_all_trades(self):
        """Iterates through all followed trades and checks for alerts.

        For each monitored trade, this method fetches the latest market data,
        runs a new analysis, and then calls `_check_for_alerts` to see if any
        noteworthy events have occurred.
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
        """Compares new analysis with the initial setup to find alertable events.

        This method checks for a wide range of events, including:
        - Price approaching key support/resistance levels.
        - Breaches of key support/resistance levels.
        - Stop-loss or profit-target hits.
        - Changes in the underlying pattern's status (e.g., activation, failure).

        It uses a set of notified events to prevent sending duplicate alerts.

        Args:
            current_price (float): The current price of the asset.
            new_analysis (Dict[str, Any]): The results from the new analysis.
            trade_data (Dict[str, Any]): The data for the monitored trade.
            trade_key (str): The unique key for the monitored trade.
        """
        chat_id = trade_data['chat_id']
        symbol = trade_data['symbol']
        notified_events = trade_data['notified_events']
        initial_rec = trade_data['initial_recommendation']
        trade_setup = initial_rec.get('trade_setup')

        # Helper function to send notification and add to notified events
        def notify(event_key: str, message: str):
            if event_key not in notified_events:
                self.notifier.send(f"**Trade Alert: {symbol} ({trade_setup.timeframe})**\n{message}", chat_id)
                notified_events.add(event_key)

        # --- 1. Check for approaching key levels from the new analysis ---
        # Supports
        for support in new_analysis.get('supports', []):
            level_val = support.value
            if current_price > level_val and abs(current_price - level_val) / level_val < self.proximity_threshold:
                notify(f"approach_support_{level_val:.2f}", f"⚠️ **Approaching Support Alert:** Price is approaching support level ${level_val:,.2f} ({support.name}).")

        # Resistances
        for res in new_analysis.get('resistances', []):
            level_val = res.value
            if current_price < level_val and abs(current_price - level_val) / level_val < self.proximity_threshold:
                notify(f"approach_res_{level_val:.2f}", f"⚠️ **Approaching Resistance Alert:** Price is approaching resistance level ${level_val:,.2f} ({res.name}).")

        # Dynamic levels from other analysis (e.g., trendlines, channels, MAs)
        other_analysis = new_analysis.get('other_analysis', {})
        for analysis_name, results in other_analysis.items():
            if isinstance(results, dict):
                # Check for S/R levels within other analyses
                for s_or_r_list in ['supports', 'resistances']:
                    for level in results.get(s_or_r_list, []):
                        level_val = level.value
                        is_support = s_or_r_list == 'supports'
                        if is_support and current_price > level_val and abs(current_price - level_val) / level_val < self.proximity_threshold:
                            notify(f"approach_dyn_support_{analysis_name}_{level.name}", f"📈 **Approaching Dynamic Support:** Price is approaching {level.name} at ${level_val:,.2f}.")
                        elif not is_support and current_price < level_val and abs(current_price - level_val) / level_val < self.proximity_threshold:
                            notify(f"approach_dyn_res_{analysis_name}_{level.name}", f"📉 **Approaching Dynamic Resistance:** Price is approaching {level.name} at ${level_val:,.2f}.")

        # --- 2. Check for breaches of key trade setup levels (including generic S/R) ---
        # Generic S/R breaks from initial analysis
        initial_analysis = initial_rec.get('raw_analysis', {})
        for support in initial_analysis.get('supports', []):
            if current_price < support.value:
                notify(f"support_break_{support.value:.2f}", f"💥 **Support Break Alert:** Price broke the support level ${support.value:,.2f} ({support.name}).")

        for res in initial_analysis.get('resistances', []):
            if current_price > res.value:
                notify(f"res_break_{res.value:.2f}", f"💥 **Resistance Break Alert:** Price broke the resistance level ${res.value:,.2f} ({res.name}).")

        # Stop Loss
        if current_price < trade_setup.stop_loss:
            notify("stop_loss_hit", f"🛑 **Stop Loss Hit!** The stop-loss price of ${trade_setup.stop_loss:,.2f} was reached.")
            if self.followed_trades.get(trade_key):
                 del self.followed_trades[trade_key]
            return # Stop further checks

        # Targets
        if trade_setup.target2 and current_price >= trade_setup.target2:
             notify("target2_hit", f"🎯 **Target 2 Hit!** The second target of ${trade_setup.target2:,.2f} was reached.")
             if self.followed_trades.get(trade_key):
                 del self.followed_trades[trade_key]
             return # Stop further checks
        elif current_price >= trade_setup.target1:
             notify("target1_hit", f"🎯 **Target 1 Hit!** The first target of ${trade_setup.target1:,.2f} was reached.")

        # --- 3. Check for pattern status changes and activations ---
        initial_pattern = trade_setup.raw_pattern_data
        new_pattern_list = [p for p in new_analysis.get('patterns', []) if p.name == initial_pattern.get('name')]

        if new_pattern_list:
            new_pattern = new_pattern_list[0]
            initial_status = initial_pattern.get('status')
            new_status = new_pattern.status

            if new_status != initial_status:
                event_key = f"pattern_status_{new_status}"
                if new_status == 'Active':
                    message = f"✅ **Trade Activated!** The {initial_pattern.get('name')} pattern was activated at ${current_price:,.2f}."
                elif new_status == 'Failed':
                    message = f"❌ **Trade Failed!** The {initial_pattern.get('name')} pattern failed to maintain its conditions."
                else:
                    message = f"🔔 **Pattern Update:** The status of the {initial_pattern.get('name')} pattern has changed to '{new_status}'."

                notify(event_key, message)

                # If the pattern has reached a terminal state, remove it from monitoring
                if new_status in ['Active', 'Failed', 'Cancelled']:
                    logger.info(f"Pattern for {trade_key} is terminal ('{new_status}'). Removing from monitor.")
                    if self.followed_trades.get(trade_key):
                        del self.followed_trades[trade_key]
                    return # Stop further checks for this trade
