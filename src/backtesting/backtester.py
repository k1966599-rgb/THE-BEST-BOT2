import pandas as pd
from typing import Dict, Any
from ..strategies.base_strategy import BaseStrategy
import logging

# Use the same logger as the rest of the application
logger = logging.getLogger(__name__)

class Backtester:
    """
    A simple event-driven backtesting engine to evaluate strategy performance.
    """
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 10000.0, commission_rate: float = 0.001):
        """
        Initializes the Backtester.

        Args:
            strategy: An instance of a class that inherits from BaseStrategy.
            initial_capital: The starting capital for the backtest.
            commission_rate: The trading commission per trade (e.g., 0.001 for 0.1%).
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

        # State variables
        self.capital = self.initial_capital
        self.position_size = 0.0  # Represents the amount of the asset held
        self.trades = []

    def run(self, data: pd.DataFrame):
        """
        Runs the backtest on the given historical data.

        Args:
            data (pd.DataFrame): DataFrame containing OHLCV data, indexed by timestamp.
        """
        logger.info(f"--- Starting Backtest for Strategy: {self.strategy.__class__.__name__} ---")
        if data.empty:
            logger.warning("Data is empty. Aborting backtest.")
            return

        for i in range(1, len(data)):
            # The strategy gets a window of data up to the current point to make a decision
            current_data_window = data.iloc[0:i].copy()
            signal_info = self.strategy.generate_signals(current_data_window)
            signal = signal_info.get('signal')

            latest_price = data['close'].iloc[i]

            # --- Execute BUY signal ---
            if signal == 'BUY' and self.position_size == 0:
                # Position sizing: use 99% of available capital to be safe
                amount_to_buy = (self.capital * 0.99) / latest_price
                cost = amount_to_buy * latest_price * (1 + self.commission_rate)

                self.position_size = amount_to_buy
                self.capital -= cost
                self.trades.append({'timestamp': data.index[i], 'type': 'BUY', 'price': latest_price, 'amount': amount_to_buy, 'cost': cost})
                logger.info(f"[{data.index[i]}] BUY signal executed at {latest_price:.2f}. Reason: {signal_info.get('reason')}")

            # --- Execute SELL signal ---
            elif signal == 'SELL' and self.position_size > 0:
                revenue = self.position_size * latest_price * (1 - self.commission_rate)
                profit = revenue - self.trades[-1]['cost']

                self.capital += revenue
                self.trades.append({'timestamp': data.index[i], 'type': 'SELL', 'price': latest_price, 'amount': self.position_size, 'profit': profit})
                logger.info(f"[{data.index[i]}] SELL signal executed at {latest_price:.2f}. Profit: ${profit:.2f}. Reason: {signal_info.get('reason')}")
                self.position_size = 0.0

        # If the position is still open at the end, close it at the last known price
        if self.position_size > 0:
            last_price = data['close'].iloc[-1]
            revenue = self.position_size * last_price * (1 - self.commission_rate)
            profit = revenue - self.trades[-1]['cost']
            self.capital += revenue
            self.trades.append({'timestamp': data.index[-1], 'type': 'CLOSE_AT_END', 'price': last_price, 'amount': self.position_size, 'profit': profit})
            logger.info(f"Closing open position at end of data. Price: {last_price:.2f}. Profit: ${profit:.2f}")
            self.position_size = 0.0

        self.print_results()

    def print_results(self):
        """
        Calculates and prints the performance metrics of the backtest.
        """
        logger.info("\n--- Backtest Results ---")
        final_capital = self.capital
        total_return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100

        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Capital:   ${final_capital:,.2f}")
        logger.info(f"Total Return:    {total_return_pct:.2f}%")

        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] in ('SELL', 'CLOSE_AT_END')]

        total_trades = len(sell_trades)
        wins = sum(1 for t in sell_trades if t['profit'] > 0)
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        logger.info(f"Total Closed Trades: {total_trades}")
        logger.info(f"Win Rate:        {win_rate:.2f}%")
        logger.info(f"Wins:            {wins}")
        logger.info(f"Losses:          {losses}")


if __name__ == '__main__':
    # This allows running the backtester directly for testing purposes.
    # To run: python -m src.backtesting.backtester

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    from src.backtesting.data_loader import load_backtest_data
    from src.strategies.fibo_strategy import FiboStrategy
    from src.config import get_config

    logger.info("--- Setting up backtest environment ---")

    # 1. Load Data
    symbol = 'BTC-USDT'
    timeframe = '4H'
    data = load_backtest_data(symbol, timeframe)

    if data is not None and not data.empty:
        # 2. Initialize Strategy
        config = get_config()
        config['strategy_params'] = {
            'rsi_period': 14,
            'sma_period_fast': 20,
            'sma_period_slow': 50,
            'fib_lookback': 60
        }
        fibo_strategy = FiboStrategy(config)

        # 3. Initialize and Run Backtester
        backtester = Backtester(strategy=fibo_strategy, initial_capital=10000.0, commission_rate=0.001)
        backtester.run(data)
    else:
        logger.error("Could not load data. Aborting backtest.")
