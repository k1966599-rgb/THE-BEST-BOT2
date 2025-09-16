import time
import logging
import pandas as pd
from typing import Dict, Any

from ..data_retrieval.data_fetcher import DataFetcher
from ..strategies.base_strategy import BaseStrategy
from ..execution.exchange_trader import ExchangeTrader, AuthenticationError
from ..risk_management.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class TradingEngine:
    """
    The main engine for the live trading bot.
    Connects data fetching, strategy, risk management, and execution.
    """
    def __init__(self, config: Dict[str, Any], strategy: BaseStrategy):
        self.config = config
        self.strategy = strategy

        self.fetcher = DataFetcher(config)
        self.trader = ExchangeTrader(config)
        self.risk_manager = RiskManager(config.get('risk_management', {}))

        # Get trading parameters from config
        trading_config = config.get('trading', {})
        self.symbol = trading_config.get('WATCHLIST', ['BTC-USDT'])[0]
        self.timeframe = trading_config.get('TIMEFRAMES', ['1H'])[0]
        self.trade_amount = trading_config.get('TRADE_AMOUNT', '0.001')

        # Interval between trading cycles in seconds
        self.sleep_interval = 300  # 5 minutes

    def run(self):
        """
        The main loop of the trading bot.
        """
        logger.info(f"--- Starting Trading Engine for {self.symbol} on {self.timeframe} ---")
        logger.info(f"Using strategy: {self.strategy.__class__.__name__}")
        if self.config.get('exchange', {}).get('SANDBOX_MODE'):
            logger.warning("Bot is running in SANDBOX MODE. No real funds will be used.")
        else:
            logger.warning("Bot is running in LIVE MODE. Real funds will be used.")

        while True:
            try:
                self._run_iteration()
                logger.info(f"Iteration complete. Sleeping for {self.sleep_interval / 60:.1f} minutes...")
                time.sleep(self.sleep_interval)
            except AuthenticationError as e:
                logger.error(f"Authentication Error: {e}")
                logger.error("The bot cannot continue without valid API credentials.")
                logger.info("Please check your .env file and restart the bot.")
                break  # Exit the loop on auth error
            except KeyboardInterrupt:
                logger.info("Bot stopped manually. Exiting.")
                break
            except Exception as e:
                logger.exception(f"An unexpected error occurred in the main loop: {e}")
                logger.info("Waiting for 60 seconds before retrying...")
                time.sleep(60)

    def _run_iteration(self):
        """
        Executes a single trading cycle: manage risk, fetch data, get signal, place order.
        """
        logger.info("Running new trading iteration...")

        # 1. Manage risk for any open positions
        open_position = self._check_and_manage_open_position()

        # 2. Fetch latest market data
        data_dict = self.fetcher.fetch_historical_data(self.symbol, self.timeframe, limit=300)

        if not data_dict or 'data' not in data_dict or not data_dict['data']:
            logger.warning("Could not fetch valid data. Skipping this iteration.")
            return

        df = pd.DataFrame(data_dict['data'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 3. Generate signal from strategy
        signal_info = self.strategy.generate_signals(df)
        signal = signal_info.get('signal')
        logger.info(f"Strategy generated signal: {signal} | Reason: {signal_info.get('reason')}")

        # 4. Execute trade based on signal and current position
        if signal == 'BUY' and not open_position:
            logger.info(f"BUY signal received. Attempting to place market order for {self.trade_amount} {self.symbol}.")
            order_result = self.trader.place_order(
                symbol=self.symbol,
                side='buy',
                order_type='market',
                amount=self.trade_amount
            )
            if order_result:
                logger.info(f"Successfully placed BUY order. Details: {order_result}")
            else:
                logger.error("Failed to place BUY order.")

        elif signal == 'SELL' and open_position:
            logger.info(f"SELL signal received. Attempting to close position for {self.symbol}.")
            # The amount to sell should be the size of the open position
            position_size = open_position.get('pos')
            order_result = self.trader.place_order(
                symbol=self.symbol,
                side='sell',
                order_type='market',
                amount=position_size
            )
            if order_result:
                logger.info(f"Successfully placed SELL order. Details: {order_result}")
            else:
                logger.error("Failed to place SELL order.")

        elif signal == 'HOLD':
            logger.info("HOLD signal received. No action taken.")
        else:
            logger.info(f"Signal '{signal}' received, but conditions not met for trading. No action taken.")

    def _check_and_manage_open_position(self) -> Dict[str, Any] or None:
        """
        Checks if there is an open position for the symbol and manages its risk.
        Returns the position details if it exists, otherwise None.
        """
        position = self.trader.get_position(self.symbol)
        if position:
            logger.info(f"Found open position: {position}")
            # The position object from OKX needs to be adapted for the risk manager
            # This is a simplification; a real implementation would need more robust mapping
            risk_assessment_position = {
                'id': position.get('posId'),
                'unrealized_pnl': float(position.get('upl', 0))
            }
            risk_action = self.risk_manager.assess_risk(risk_assessment_position)

            if risk_action == 'CLOSE':
                logger.warning(f"Risk Manager triggered CLOSE for position {position.get('posId')}. Closing position.")
                position_size = position.get('pos')
                self.trader.place_order(
                    symbol=self.symbol,
                    side='sell',
                    order_type='market',
                    amount=position_size
                )
                return None  # Position is being closed
            return position
        return None
