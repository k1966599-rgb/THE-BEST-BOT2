import pandas as pd
from typing import Dict, Any

from .base_strategy import BaseStrategy
from ..utils.indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_bollinger_bands,
    find_swing_points,
    calculate_fib_extensions,
    calculate_macd
)
from ..utils.patterns import get_candlestick_pattern

class FiboAnalyzer(BaseStrategy):
    """
    An enhanced analyzer based on Fibonacci retracement levels, with confirmations
    from technical indicators and candlestick patterns, designed to populate a
    detailed analysis template.
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
            self.volume_lookback = strategy_params.get('volume_lookback', 20)
        except KeyError:
            print("Warning: FiboStrategy params not found in config. Using default values.")
            self.rsi_period = 14
            self.sma_period_fast = 50
            self.sma_period_slow = 200
            self.fib_lookback = 50
            self.bb_window = 20
            self.volume_lookback = 20

    def _get_confirmations(self, data: pd.DataFrame, fib_618_val: float, pattern: str) -> Dict[str, bool]:
        """Helper to get all boolean confirmations for the template."""
        latest = data.iloc[-1]
        avg_volume = data['volume'].iloc[-self.volume_lookback:-1].mean()

        return {
            "break_618": latest['close'] > fib_618_val,
            "daily_close_above_fib": latest['close'] > fib_618_val, # Simplified for now
            "high_volume": latest['volume'] > (avg_volume * 1.25),
            "rsi_above_50": latest['rsi'] > 50,
            "reversal_candle": pattern in ["Bullish Engulfing", "Hammer", "Doji"],
            "is_hammer": pattern == "Hammer",
            "is_engulfing": pattern == "Bullish Engulfing",
            "break_doji": False, # Complex logic, placeholder
            "close_above_doji": False, # Complex logic, placeholder
            "volume_confirm_pattern": False, # Complex logic, placeholder
            "trade_close_4h": False, # Requires multi-timeframe logic, placeholder
            "trade_volume_150": latest['volume'] > (avg_volume * 1.5),
            "trade_macd_positive": latest['macd'] > latest['signal_line'],
            "trade_trendline_break": False, # Requires trendline logic, placeholder
        }

    def _generate_scenarios(self, signal: str, price: float, swing_high: float, swing_low: float) -> Dict[str, Any]:
        """Helper to generate potential scenarios based on the signal."""
        # This is a simplified model for scenario generation.
        # A real-world implementation would be much more complex.
        if signal == 'BUY':
            return {
                "scenario1": {"title": "صعود تدريجي", "prob": 65, "target": swing_high * 1.02, "entry": price * 1.01, "stop_loss": price * 0.99},
                "scenario2": {"title": "تذبذب جانبي", "prob": 25, "target": price * 1.01, "entry": price, "stop_loss": price * 0.99},
                "scenario3": {"title": "هبوط إضافي", "prob": 10, "target": swing_low, "entry": price * 0.99, "stop_loss": price * 1.01},
            }
        # Default scenarios for HOLD/SELL
        return {
            "scenario1": {"title": "تذبذب جانبي", "prob": 60, "target": price * 1.01, "entry": price, "stop_loss": price * 0.99},
            "scenario2": {"title": "هبوط تدريجي", "prob": 30, "target": swing_low, "entry": price * 0.99, "stop_loss": price * 1.01},
            "scenario3": {"title": "صعود محتمل", "prob": 10, "target": swing_high, "entry": price * 1.01, "stop_loss": price * 0.99},
        }

    def get_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates a professional analysis designed to populate the detailed template.
        """
        if data.empty or len(data) < self.fib_lookback:
            return {'signal': 'HOLD', 'reason': 'Not enough data for analysis.'}

        # --- 1. Calculate All Indicators ---
        data['rsi'] = calculate_rsi(data, self.rsi_period)
        data['sma_fast'] = calculate_sma(data, self.sma_period_fast)
        data['sma_slow'] = calculate_sma(data, self.sma_period_slow)
        data = data.join(calculate_bollinger_bands(data, window=self.bb_window))
        macd_df = calculate_macd(data)
        data['macd'] = macd_df['macd']
        data['signal_line'] = macd_df['signal_line']

        # --- 2. Identify Key Points & Patterns ---
        swing_points = find_swing_points(data, lookback=self.fib_lookback)
        swing_high_info = swing_points['swing_high']
        swing_low_info = swing_points['swing_low']
        pattern = get_candlestick_pattern(data.iloc[-2:])

        if not swing_high_info['price'] or not swing_low_info['price']:
             return {'signal': 'HOLD', 'reason': 'Could not determine swing points for analysis.'}

        swing_high = swing_high_info['price']
        swing_low = swing_low_info['price']

        # --- 3. Calculate Fibonacci Levels ---
        fib_levels = {
            "fib_236": swing_high - 0.236 * (swing_high - swing_low),
            "fib_382": swing_high - 0.382 * (swing_high - swing_low),
            "fib_500": swing_high - 0.500 * (swing_high - swing_low),
            "fib_618": swing_high - 0.618 * (swing_high - swing_low),
            "fib_786": swing_high - 0.786 * (swing_high - swing_low),
        }

        # --- 4. Define Trend and Signal Conditions ---
        latest = data.iloc[-1]
        is_uptrend = latest['sma_fast'] > latest['sma_slow']
        confirmations = self._get_confirmations(data, fib_levels['fib_618'], pattern)

        # --- 5. Generate Signal ---
        signal = 'HOLD'
        reason = 'No clear signal met conditions.'
        trade_info = {}

        buy_pullback_to_fib = latest['low'] <= fib_levels['fib_618'] <= latest['high']
        buy_pattern_confirm = pattern in ["Bullish Engulfing", "Hammer"]

        if is_uptrend and buy_pullback_to_fib and buy_pattern_confirm:
            signal = 'BUY'
            reason = f'Uptrend pullback to Fib level confirmed by {pattern}.'
            targets = calculate_fib_extensions(swing_high, swing_low)
            trade_info = {
                "trade_title": "شراء عند تأكيد الانعكاس",
                "trade_entry": f"{fib_levels['fib_382']:.2f}",
                "trade_target1": f"{targets[0]:.2f}",
                "trade_target2": f"{targets[1]:.2f}",
                "trade_target3": f"{swing_high + (swing_high - swing_low) * 4.236:.2f}", # Example 3rd target
                "trade_stop_loss": f"{swing_low:.2f}",
            }

        # --- 6. Generate Scenarios ---
        scenarios = self._generate_scenarios(signal, latest['close'], swing_high, swing_low)

        # --- 7. Consolidate All Data for Formatting ---
        return {
            "signal": signal,
            "reason": reason,
            "current_price": latest['close'],
            "swing_high": swing_high_info,
            "swing_low": swing_low_info,
            "fib_levels": fib_levels,
            "confirmations": confirmations,
            "pattern": pattern,
            "scenarios": scenarios,
            **trade_info,
            **confirmations # Flatten confirmations for easy access
        }
