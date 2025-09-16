import pandas as pd
from typing import Dict, Any

from .base_strategy import BaseStrategy
from ..utils.indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_bollinger_bands,
    find_swing_points,
    calculate_fib_extensions
)
from ..utils.patterns import get_candlestick_pattern

class FiboAnalyzer(BaseStrategy):
    """
    An enhanced analyzer based on Fibonacci retracement levels, with confirmations
    from technical indicators and candlestick patterns.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            strategy_params = self.config['strategy_params']['fibo_strategy']
            self.rsi_period = strategy_params.get('rsi_period', 14)
            self.sma_period_fast = strategy_params.get('sma_period_fast', 50)
            self.sma_period_slow = strategy_params.get('sma_period_slow', 200)
            self.fib_lookback = strategy_params.get('fib_lookback', 50)
            self.bb_window = strategy_params.get('bb_window', 20)
        except KeyError:
            print("Warning: FiboStrategy params not found in config. Using default values.")
            self.rsi_period = 14
            self.sma_period_fast = 50
            self.sma_period_slow = 200
            self.fib_lookback = 50
            self.bb_window = 20

    def get_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates a professional analysis based on Fibonacci levels,
        indicator confirmations, and candlestick patterns.
        """
        if data.empty or len(data) < self.fib_lookback:
            return {'signal': 'HOLD', 'reason': 'Not enough data for analysis.'}

        # --- 1. Calculate Indicators ---
        data['rsi'] = calculate_rsi(data, self.rsi_period)
        data['sma_fast'] = calculate_sma(data, self.sma_period_fast)
        data['sma_slow'] = calculate_sma(data, self.sma_period_slow)
        bb_df = calculate_bollinger_bands(data, window=self.bb_window)
        data = data.join(bb_df)

        # --- 2. Identify Swing Points and Candlestick Patterns ---
        swing_points = find_swing_points(data, lookback=self.fib_lookback)
        swing_high = swing_points['swing_high']
        swing_low = swing_points['swing_low']

        pattern = get_candlestick_pattern(data.iloc[-2:]) # Check last two candles

        if swing_high <= swing_low:
            return {'signal': 'HOLD', 'reason': 'Market is flat, cannot calculate Fibonacci levels.'}

        # --- 3. Calculate Fibonacci Levels ---
        fib_level_618 = swing_high - 0.618 * (swing_high - swing_low)
        fib_level_500 = swing_high - 0.500 * (swing_high - swing_low)
        fib_level_382 = swing_high - 0.382 * (swing_high - swing_low)

        # --- 4. Get Latest Data ---
        latest = data.iloc[-1]

        # --- 5. Define Trend and Signal Conditions ---
        is_uptrend = latest['sma_fast'] > latest['sma_slow']
        is_downtrend = latest['sma_fast'] < latest['sma_slow']

        # --- BUY Condition ---
        # Price pulls back to a key Fib level in an uptrend, confirmed by a bullish pattern.
        buy_pullback_to_fib = latest['low'] <= fib_level_618 <= latest['high'] or \
                              latest['low'] <= fib_level_500 <= latest['high']
        buy_rsi_confirm = latest['rsi'] < 45 # RSI below 45 shows pullback is not over-extended
        buy_pattern_confirm = pattern in ["Bullish Engulfing", "Hammer"]

        if is_uptrend and buy_pullback_to_fib and buy_rsi_confirm and buy_pattern_confirm:
            targets = calculate_fib_extensions(swing_high, swing_low)
            return {
                'signal': 'BUY',
                'reason': f'Uptrend pullback to Fib level confirmed by {pattern}. RSI at {latest["rsi"]:.2f}.',
                'pattern': pattern,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'targets': [f"{t:.2f}" for t in targets]
            }

        # --- SELL Condition ---
        # Price breaks below a key support (fast SMA) in a downtrend, confirmed by a bearish pattern.
        sell_price_break = latest['close'] < latest['sma_fast']
        sell_pattern_confirm = pattern == "Bearish Engulfing"

        if is_downtrend and sell_price_break and sell_pattern_confirm:
            return {
                'signal': 'SELL',
                'reason': f'Downtrend price break below SMA({self.sma_period_fast}) confirmed by {pattern}.',
                'pattern': pattern,
                'swing_high': swing_high,
                'swing_low': swing_low
            }

        return {
            'signal': 'HOLD',
            'reason': 'No clear signal met conditions.',
            'pattern': pattern,
            'rsi': f'{latest["rsi"]:.2f}',
            'trend': 'Uptrend' if is_uptrend else 'Downtrend' if is_downtrend else 'Sideways'
        }
