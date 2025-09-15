import asyncio
import logging
from typing import Dict, Any, List
import pandas as pd
import anyio
from ..data_retrieval.base_fetcher import BaseDataFetcher
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
        notifier: SimpleTelegramNotifier
    ):
        """Initializes the TradeMonitor.

        Args:
            config (Dict[str, Any]): The main configuration dictionary.
            fetcher (BaseDataFetcher): An instance of a data fetcher to get
                updated market data.
            notifier (SimpleTelegramNotifier): An instance of a notifier to
                send alerts.
        """
        self.config = config
        self.fetcher = fetcher
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
            logger.warning("محاولة متابعة صفقة بدون تفاصيل إعداد.")
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
        logger.info(f"تمت إضافة صفقة للمراقبة: {key}")

    async def run_monitoring_loop(self):
        """The main background task that periodically checks followed trades.

        This method runs an infinite loop that calls `check_all_trades` at a
        regular interval defined by `monitoring_interval_seconds`.
        """
        logger.info("🚀 بدأت حلقة مراقبة الصفقات.")
        while True:
            try:
                await self.check_all_trades()
            except Exception:
                logger.exception("حدث خطأ في حلقة مراقبة الصفقات.")

            await asyncio.sleep(self.monitoring_interval_seconds)

    async def check_all_trades(self):
        """Iterates through all followed trades and checks for alerts.

        For each monitored trade, this method fetches the latest market data,
        runs a new analysis, and then calls `_check_for_alerts` to see if any
        noteworthy events have occurred.
        """
        if not self.followed_trades:
            return

        logger.info(f"جاري فحص {len(self.followed_trades)} من الصفقات المتبعة...")
        for key, trade_data in list(self.followed_trades.items()):
            try:
                symbol = trade_data['symbol']
                timeframe = trade_data['timeframe']
                okx_symbol = symbol.replace('/', '-')

                historical_data_wrapper = await anyio.to_thread.run_sync(self.fetcher.fetch_historical_data, okx_symbol, timeframe, 90)
                if not historical_data_wrapper or not historical_data_wrapper.get('data'):
                    logger.warning(f"تعذر جلب البيانات التاريخية لـ {symbol} على {timeframe} للمراقبة.")
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

                # Initialize analysis modules for the current timeframe
                from ..analysis import (
                    TrendAnalysis, PriceChannels,
                    NewSupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
                )
                from ..indicators.technical_score import TechnicalIndicators
                from ..indicators.volume_profile import VolumeProfileAnalysis

                analysis_modules = [
                    TechnicalIndicators(config=self.config.get('analysis'), timeframe=timeframe),
                    TrendAnalysis(config=self.config.get('analysis'), timeframe=timeframe),
                    PriceChannels(config=self.config.get('analysis'), timeframe=timeframe),
                    NewSupportResistanceAnalysis(config=self.config.get('analysis'), timeframe=timeframe),
                    FibonacciAnalysis(config=self.config.get('analysis'), timeframe=timeframe),
                    ClassicPatterns(config=self.config.get('analysis'), timeframe=timeframe),
                    TrendLineAnalysis(config=self.config.get('analysis'), timeframe=timeframe),
                    VolumeProfileAnalysis(config=self.config.get('analysis'), timeframe=timeframe)
                ]
                orchestrator = AnalysisOrchestrator(analysis_modules)
                new_analysis_results = orchestrator.run(df.copy())

                await self._check_for_alerts(current_price, new_analysis_results, trade_data, key)

            except Exception as e:
                logger.exception(f"Error checking trade {key}: {e}")

    async def _check_for_alerts(self, current_price: float, new_analysis: Dict[str, Any], trade_data: Dict[str, Any], trade_key: str):
        """
        Compares the current price against key levels from the initial analysis
        and sends user-specified alerts.
        """
        chat_id = trade_data['chat_id']
        symbol = trade_data['symbol']
        timeframe = trade_data['timeframe']
        notified_events = trade_data['notified_events']
        initial_rec = trade_data['initial_recommendation']
        trade_setup = initial_rec.get('trade_setup')
        initial_analysis = initial_rec.get('raw_analysis', {})

        # Helper function to send notification and add to notified events
        def notify(event_key: str, reason: str, advice: str):
            if event_key not in notified_events:
                # User mention placeholder, can be replaced with actual mention if bot framework supports it
                mention = "@user"
                message = (
                    f"🔔 **تنبيه متابعة - {symbol}** 🔔\n\n"
                    f"الفريم: {timeframe}\n"
                    f"السعر: ${current_price:,.0f}\n"
                    f"المنشن: {mention}\n"
                    f"سبب التنبيه: {reason}\n"
                    f"نصيحة: {advice}"
                )
                self.notifier.send(message, chat_id)
                notified_events.add(event_key)

        # --- 1. Check for price hitting initial support/resistance levels ---
        all_levels = initial_analysis.get('supports', []) + initial_analysis.get('resistances', [])
        for level in all_levels:
            level_val = level.value
            is_support = 'support' in level.level_type.lower() or 'دعم' in level.name.lower()

            # Check if price is very close to the level
            if abs(current_price - level_val) / level_val < self.proximity_threshold:
                event_key = f"hit_level_{level_val:.0f}"
                if is_support:
                    reason = f"ارتداد السعر من دعم {level.name} عند ${level_val:,.0f}"
                    advice = "قد يكون ارتدادًا صعوديًا، راقب تأكيد الشمعة الحالية."
                else:
                    reason = f"ملامسة السعر لمقاومة {level.name} عند ${level_val:,.0f}"
                    advice = "قد يواجه السعر صعوبة في الاختراق، كن حذرًا من الانعكاس."

                notify(event_key, reason, advice)

        # --- 2. Check for breaches of key trade setup levels (Stop Loss / Targets) ---
        if not trade_setup:
            return

        # Stop Loss
        if current_price <= trade_setup.stop_loss:
            event_key = "stop_loss_hit"
            if event_key not in notified_events:
                self.notifier.send(f"🛑 **وقف الخسارة** 🛑\n\nتم ضرب وقف الخسارة لصفقة {symbol} على فريم {timeframe} عند سعر ${trade_setup.stop_loss:,.0f}.", chat_id)
                notified_events.add(event_key)
                if self.followed_trades.get(trade_key):
                    del self.followed_trades[trade_key]
                logger.info(f"تمت إزالة الصفقة {trade_key} بسبب ضرب وقف الخسارة.")
                return  # Stop further checks

        # Targets
        targets = sorted([t for t in [trade_setup.target1, trade_setup.target2] if t], reverse=True)
        for i, target_val in enumerate(targets):
            if target_val and current_price >= target_val:
                event_key = f"target{i+1}_hit"
                if event_key not in notified_events:
                    self.notifier.send(f"🎯 **تحقيق هدف** 🎯\n\nتم تحقيق الهدف {i+1} لصفقة {symbol} على فريم {timeframe} عند سعر ${target_val:,.0f}!", chat_id)
                    notified_events.add(event_key)
                    # If the last target is hit, remove the trade from monitoring
                    if i == 0: # This is the highest target
                         if self.followed_trades.get(trade_key):
                            del self.followed_trades[trade_key]
                         logger.info(f"تمت إزالة الصفقة {trade_key} بسبب تحقيق جميع الأهداف.")
                         return # Stop further checks
