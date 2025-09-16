import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from .base_analysis import BaseAnalysis
from .data_models import Level

logger = logging.getLogger(__name__)

class FibonacciAnalysis(BaseAnalysis):
    """
    Performs Fibonacci analysis by identifying the most recent significant swing
    and calculating retracement levels.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_ratios = [1.618, 2.618]

    def analyze(self, df: pd.DataFrame, highs: List[Dict], lows: List[Dict]) -> Dict[str, List[Level]]:
        if len(highs) < 1 or len(lows) < 1:
            return {'supports': [], 'resistances': []}

        current_price = df['close'].iloc[-1]

        # Determine trend using EMAs from the indicators applied in the orchestrator
        ema_short_col = f'ema_{self.config.get("TREND_SHORT_PERIOD", 20)}'
        ema_long_col = f'ema_{self.config.get("TREND_LONG_PERIOD", 100)}'
        is_uptrend = df[ema_short_col].iloc[-1] > df[ema_long_col].iloc[-1]

        swing_high = None
        swing_low = None

        # Find the most recent, significant swing
        if is_uptrend:
            # In an uptrend, we look for a swing from a low to a high.
            # The most recent high is our swing high.
            last_high = max(highs, key=lambda x: x['index'])
            # The swing low is the lowest point before that high.
            relevant_lows = [l for l in lows if l['index'] < last_high['index']]
            if not relevant_lows: return {'supports': [], 'resistances': []}
            swing_low = min(relevant_lows, key=lambda x: x['price'])
            swing_high = last_high
        else: # Downtrend
            # In a downtrend, we look for a swing from a high to a low.
            # The most recent low is our swing low.
            last_low = min(lows, key=lambda x: x['index'])
            # The swing high is the highest point before that low.
            relevant_highs = [h for h in highs if h['index'] < last_low['index']]
            if not relevant_highs: return {'supports': [], 'resistances': []}
            swing_high = max(relevant_highs, key=lambda x: x['price'])
            swing_low = last_low

        if not swing_high or not swing_low:
            return {'supports': [], 'resistances': []}

        price_range = swing_high['price'] - swing_low['price']
        if price_range <= 0:
            return {'supports': [], 'resistances': []}

        support_levels = []
        resistance_levels = []

        # Calculate Retracement Levels
        for ratio in self.retracement_ratios:
            if is_uptrend:
                level_val = swing_high['price'] - (price_range * ratio)
            else:
                level_val = swing_low['price'] + (price_range * ratio)

            level_type = 'support' if level_val < current_price else 'resistance'
            quality = "Strong" if ratio == 0.618 else ("Medium" if ratio == 0.5 else "Weak")

            template_key = None
            if ratio == 0.618: template_key = 'fib_support_0_618'
            elif ratio == 0.5: template_key = 'fib_support_0_5'

            level = Level(
                name=f"Fibonacci Retracement {ratio}", value=round(level_val, 4),
                level_type=level_type, quality=quality, template_key=template_key
            )

            if level_type == 'support':
                support_levels.append(level)
            else:
                resistance_levels.append(level)

        # Calculate Extension Levels
        for ratio in self.extension_ratios:
            if is_uptrend:
                level_val = swing_high['price'] + (price_range * (ratio - 1))
            else:
                level_val = swing_low['price'] - (price_range * (ratio - 1))

            template_key = 'fib_resistance_1_618' if ratio == 1.618 else None
            level = Level(
                name=f"Fibonacci Extension {ratio}", value=round(level_val, 4),
                level_type='resistance' if is_uptrend else 'support', quality="Target",
                template_key=template_key
            )
            if level.level_type == 'resistance':
                resistance_levels.append(level)
            else:
                support_levels.append(level)

        return {
            'supports': sorted(support_levels, key=lambda x: x.value, reverse=True),
            'resistances': sorted(resistance_levels, key=lambda x: x.value)
        }
