import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis

class FibonacciAnalysis(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback_period = overrides.get('FIB_LOOKBACK', self.config.get('FIB_LOOKBACK', 90))
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.lookback_period:
            return {'error': 'Not enough data for Fibonacci analysis.'}

        data = df.tail(self.lookback_period)

        # Find the highest high and lowest low in the lookback period
        highest_high = data['high'].max()
        lowest_low = data['low'].min()

        price_range = highest_high - lowest_low
        if price_range == 0:
            return {'error': 'No price range for Fibonacci analysis.'}

        current_price = data['close'].iloc[-1]

        # Determine if the primary trend in the lookback period is up or down
        is_uptrend = data['close'].iloc[-1] > data['close'].iloc[0]

        retracements = {}
        if is_uptrend:
            # In an uptrend, retracements are measured down from the high
            for ratio in self.retracement_ratios:
                level = highest_high - (price_range * ratio)
                retracements[f'Retracement_{ratio}'] = level
        else:
            # In a downtrend, retracements are measured up from the low
            for ratio in self.retracement_ratios:
                level = lowest_low + (price_range * ratio)
                retracements[f'Retracement_{ratio}'] = level

        # Classify levels as support or resistance
        support_levels = {f'{ratio*100:.1f}%': round(level, 2) for ratio, level in retracements.items() if level < current_price}
        resistance_levels = {f'{ratio*100:.1f}%': round(level, 2) for ratio, level in retracements.items() if level >= current_price}

        # Scoring logic
        fib_score = 0
        for level in support_levels.values():
            # Higher score if price is close to a support level
            distance_factor = 1 - min(abs(current_price - level) / current_price, 1)
            fib_score += distance_factor * 2 # Max score of 2 per support

        for level in resistance_levels.values():
            distance_factor = 1 - min(abs(current_price - level) / current_price, 1)
            fib_score -= distance_factor * 2

        return {
            'supports': support_levels,
            'resistances': resistance_levels,
            'fib_score': round(fib_score, 2)
        }
