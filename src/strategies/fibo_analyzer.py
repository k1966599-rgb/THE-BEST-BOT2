import pandas as pd
from typing import Dict, Any
from src.data_retrieval.data_fetcher import DataFetcher

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

    def __init__(self, config: Dict[str, Any], fetcher: DataFetcher):
        super().__init__(config)
        self.fetcher = fetcher
        try:
            strategy_params = self.config['strategy_params']['fibo_strategy']
            self.rsi_period = strategy_params.get('rsi_period', 14)
            self.sma_period_fast = strategy_params.get('sma_period_fast', 50)
            self.sma_period_slow = strategy_params.get('sma_period_slow', 200)
            self.fib_lookback = strategy_params.get('fib_lookback', 50)
            self.bb_window = strategy_params.get('bb_window', 20)
            self.volume_lookback = strategy_params.get('volume_lookback', 20)
        except KeyError:
            # Using default values
            self.rsi_period, self.sma_period_fast, self.sma_period_slow, self.fib_lookback, self.bb_window, self.volume_lookback = 14, 50, 200, 50, 20, 20

    def _get_confirmations(self, data: pd.DataFrame, fib_618_val: float, pattern: str, daily_trend_is_up: bool, prev_pattern: str) -> Dict[str, bool]:
        """Helper to get all boolean confirmations for the template."""
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        avg_volume = data['volume'].iloc[-self.volume_lookback:-1].mean()

        doji_breakout = prev_pattern == "Doji" and latest['close'] > previous['high']

        return {
            "break_618": latest['close'] > fib_618_val,
            "daily_close_above_fib": daily_trend_is_up,
            "high_volume": latest['volume'] > (avg_volume * 1.25),
            "rsi_above_50": latest['rsi'] > 50,
            "reversal_candle": pattern in ["Bullish Engulfing", "Hammer"] or doji_breakout,
            "is_hammer": pattern == "Hammer",
            "is_engulfing": pattern == "Bullish Engulfing",
            "break_doji": doji_breakout,
            "close_above_doji": doji_breakout, # Same condition for this template line
            "volume_confirm_pattern": latest['volume'] > avg_volume if doji_breakout else False,
            "trade_close_4h": False, # Placeholder
            "trade_volume_150": latest['volume'] > (avg_volume * 1.5),
            "trade_macd_positive": latest['macd'] > latest['signal_line'],
            "trade_trendline_break": False, # Placeholder
        }

    def _generate_scenarios(self, signal: str, fib_levels: Dict[str, float], swing_high: float, swing_low: float) -> Dict[str, Any]:
        """Helper to generate potential scenarios based on the signal and calculated levels."""
        if signal == 'BUY':
            scen1 = {"title": "صعود من المستوى الذهبي", "prob": 65, "target": fib_levels['fib_236'], "entry": fib_levels['fib_618'], "stop_loss": swing_low}
        elif signal == 'SELL':
            scen1 = {"title": "هبوط بعد كسر الدعم", "prob": 65, "target": swing_low, "entry": fib_levels['fib_236'], "stop_loss": fib_levels['fib_500']}
        else: # HOLD
            scen1 = {"title": "تذبذب بين الدعم والمقاومة", "prob": 60, "target": fib_levels['fib_382'], "entry": fib_levels['fib_618'], "stop_loss": swing_low}
        scen2 = {"title": "تذبذب جانبي", "prob": 25, "target": fib_levels['fib_382'], "entry": fib_levels['fib_500'], "stop_loss": fib_levels['fib_786']}
        if signal in ['BUY', 'HOLD']:
            scen3 = {"title": "انهيار السعر للأسفل", "prob": 10, "target": swing_low * 0.95, "entry": swing_low, "stop_loss": fib_levels['fib_786']}
        else: # SELL
            scen3 = {"title": "انعكاس قوي للأعلى", "prob": 10, "target": swing_high, "entry": fib_levels['fib_236'], "stop_loss": swing_low}
        return {"scenario1": scen1, "scenario2": scen2, "scenario3": scen3}

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generates a professional analysis designed to populate the detailed template."""
        if data.empty or len(data) < self.fib_lookback:
            return {'signal': 'HOLD', 'reason': 'Not enough data for analysis.'}

        # --- Multi-Timeframe Analysis (MTA) ---
        daily_trend_is_up = True # Default to true if it's the daily chart itself
        if timeframe != '1D':
            daily_data_dict = self.fetcher.fetch_historical_data(symbol, '1D', limit=self.sma_period_slow + 5)
            if daily_data_dict and daily_data_dict.get('data'):
                df_daily = pd.DataFrame(daily_data_dict['data'])
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
                for col in numeric_cols:
                    df_daily[col] = pd.to_numeric(df_daily[col], errors='coerce')
                df_daily.dropna(inplace=True)

                df_daily['sma_fast'] = calculate_sma(df_daily, self.sma_period_fast)
                df_daily['sma_slow'] = calculate_sma(df_daily, self.sma_period_slow)
                daily_trend_is_up = df_daily.iloc[-1]['sma_fast'] > df_daily.iloc[-1]['sma_slow']

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
        # Get pattern of the latest candle, and the one before it
        pattern = get_candlestick_pattern(data.iloc[-2:])
        prev_pattern = get_candlestick_pattern(data.iloc[-3:-1])

        if not swing_high_info['price'] or not swing_low_info['price']:
             return {'signal': 'HOLD', 'reason': 'Could not determine swing points for analysis.'}
        swing_high, swing_low = swing_high_info['price'], swing_low_info['price']

        # --- 3. Calculate Fibonacci Levels ---
        fib_levels = {"fib_236": swing_high - 0.236 * (swing_high - swing_low), "fib_382": swing_high - 0.382 * (swing_high - swing_low), "fib_500": swing_high - 0.500 * (swing_high - swing_low), "fib_618": swing_high - 0.618 * (swing_high - swing_low), "fib_786": swing_high - 0.786 * (swing_high - swing_low)}

        # --- 4. Define Trend and Signal Conditions ---
        latest = data.iloc[-1]
        is_uptrend = latest['sma_fast'] > latest['sma_slow']
        confirmations = self._get_confirmations(data, fib_levels['fib_618'], pattern, daily_trend_is_up, prev_pattern)

        # --- 5. Generate Signal ---
        signal, reason, trade_info = 'HOLD', 'No clear signal met conditions.', {}
        buy_pullback_to_fib = latest['low'] <= fib_levels['fib_618'] <= latest['high']
        # A buy signal is stronger if confirmed by a reversal pattern or a doji breakout, and with the daily trend
        buy_pattern_confirm = pattern in ["Bullish Engulfing", "Hammer"] or confirmations["break_doji"]

        if is_uptrend and daily_trend_is_up and buy_pullback_to_fib and buy_pattern_confirm:
            signal = 'BUY'
            reason = f'Uptrend on both {timeframe} and 1D. Pullback to Fib level confirmed by {pattern}.'
            targets = calculate_fib_extensions(swing_high, swing_low)
            trade_info = {"trade_title": "شراء عند تأكيد الانعكاس", "trade_entry": f"{fib_levels['fib_382']:.2f}", "trade_target1": f"{targets[0]:.2f}", "trade_target2": f"{targets[1]:.2f}", "trade_target3": f"{swing_high + (swing_high - swing_low) * 4.236:.2f}", "trade_stop_loss": f"{swing_low:.2f}"}

        # --- 6. Generate Scenarios ---
        scenarios = self._generate_scenarios(signal, fib_levels, swing_high, swing_low)

        # --- 7. Consolidate All Data for Formatting ---
        return {"signal": signal, "reason": reason, "current_price": latest['close'], "swing_high": swing_high_info, "swing_low": swing_low_info, "fib_levels": fib_levels, "confirmations": confirmations, "pattern": pattern, "scenarios": scenarios, **trade_info, **confirmations}
