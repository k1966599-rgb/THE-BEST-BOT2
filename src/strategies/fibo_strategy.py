import pandas as pd
from typing import Dict, Any

from .base_strategy import BaseStrategy
from ..utils.indicators import calculate_rsi, calculate_sma, calculate_bollinger_bands

class FiboStrategy(BaseStrategy):
    """
    A strategy based on Fibonacci retracement levels, with confirmations
    from other technical indicators and candlestick patterns.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Strategy-specific parameters are now loaded from the centralized config
        try:
            strategy_params = self.config['strategy_params']['fibo_strategy']
            self.rsi_period = strategy_params.get('rsi_period', 14)
            self.sma_period_fast = strategy_params.get('sma_period_fast', 50)
            self.sma_period_slow = strategy_params.get('sma_period_slow', 200)
            self.fib_lookback = strategy_params.get('fib_lookback', 50)
            self.bb_window = strategy_params.get('bb_window', 20)
        except KeyError:
            # Handle cases where the strategy config might be missing
            # You could log a warning and use default values
            print("Warning: FiboStrategy params not found in config. Using default values.")
            self.rsi_period = 14
            self.sma_period_fast = 50
            self.sma_period_slow = 200
            self.fib_lookback = 50
            self.bb_window = 20

    def generate_signals(self, data: pd.DataFrame) -> Dict[str, str]:
        """
        Generates trading signals based on Fibonacci levels and confirmations.
        """
        if data.empty or len(data) < self.fib_lookback:
            return {'signal': 'HOLD', 'reason': 'Not enough data for analysis.'}

        # --- 1. Calculate Indicators ---
        data['rsi'] = calculate_rsi(data, self.rsi_period)
        data['sma_fast'] = calculate_sma(data, self.sma_period_fast)
        data['sma_slow'] = calculate_sma(data, self.sma_period_slow)
        bb_df = calculate_bollinger_bands(data, window=self.bb_window)
        data['bb_lower'] = bb_df['lower_band']
        data['bb_upper'] = bb_df['upper_band']


        # --- 2. Identify Swing Highs and Lows ---
        # TODO: Implement more robust logic to find significant swing points.
        # For now, we use a simple lookback period. A better approach would be
        # to use algorithms like Zig Zag or peak/trough detection.
        recent_data = data.iloc[-self.fib_lookback:]
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()

        if swing_high == swing_low:
             return {'signal': 'HOLD', 'reason': 'Market is flat, cannot calculate Fibonacci levels.'}

        # --- 3. Calculate Fibonacci Retracement Levels ---
        fib_level_618 = swing_high - 0.618 * (swing_high - swing_low)
        fib_level_382 = swing_high - 0.382 * (swing_high - swing_low)

        # --- 4. Get the latest candle data ---
        latest = data.iloc[-1]

        # --- 5. Define Trend and Signal Conditions ---
        is_uptrend = latest['sma_fast'] > latest['sma_slow']
        is_downtrend = latest['sma_fast'] < latest['sma_slow']

        # --- BUY Condition ---
        # 1. Must be in an uptrend.
        # 2. Price must pull back to a key Fibonacci level (e.g., 61.8%).
        # 3. RSI should be oversold or neutral (e.g., < 40), suggesting the pullback is losing steam.
        # 4. Price should be near or below the lower Bollinger Band, indicating a potential bounce.
        buy_pullback_to_fib = latest['low'] <= fib_level_618 <= latest['high']
        buy_rsi_confirm = latest['rsi'] < 40
        buy_bb_confirm = latest['close'] < latest['bb_lower']

        if is_uptrend and buy_pullback_to_fib and buy_rsi_confirm and buy_bb_confirm:
            return {
                'signal': 'BUY',
                'reason': f'Uptrend pullback to {fib_level_618:.2f} (61.8% Fib). RSI: {latest["rsi"]:.2f}. Price below lower BB.'
            }

        # --- SELL Condition (to close a position) ---
        # 1. Must be in a downtrend.
        # 2. Price breaks below a key support level (e.g., the fast SMA).
        # 3. RSI is trending down.
        sell_price_break = latest['close'] < latest['sma_fast']
        sell_rsi_confirm = latest['rsi'] < 50 # Example: RSI showing bearish momentum

        if is_downtrend and sell_price_break and sell_rsi_confirm:
             return {
                 'signal': 'SELL',
                 'reason': f'Downtrend with price below SMA({self.sma_period_fast}). RSI: {latest["rsi"]:.2f}.'
             }

        # TODO: Add more advanced candlestick pattern recognition (e.g., bullish/bearish engulfing).

        return {'signal': 'HOLD', 'reason': 'No clear signal met conditions.'}
