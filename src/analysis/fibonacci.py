import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from .base_analysis import BaseAnalysis
from .data_models import Level

logger = logging.getLogger(__name__)

class FibonacciAnalysis(BaseAnalysis):
    """Performs Fibonacci analysis to find support and resistance levels."""
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback_period = overrides.get('FIB_LOOKBACK', self.config.get('FIB_LOOKBACK', 180)) # Increased from 90
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        self.extension_ratios = [1.172, 1.618, 2.618]

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        if len(df) < self.lookback_period:
            return {'supports': [], 'resistances': []}

        data = df.tail(self.lookback_period)
        highest_high = data['high'].max()
        lowest_low = data['low'].min()
        price_range = highest_high - lowest_low

        if price_range == 0:
            return {'supports': [], 'resistances': []}

        current_price = data['close'].iloc[-1]

        ema_short_period = self.config.get('TREND_SHORT_PERIOD', 20)
        ema_long_period = self.config.get('TREND_LONG_PERIOD', 100)

        ema_short_col = f'EMA_{ema_short_period}'
        ema_long_col = f'EMA_{ema_long_period}'

        def get_val(col_name):
            if col_name.lower() in data.columns:
                return data[col_name.lower()].iloc[-1]
            if col_name.upper() in data.columns:
                return data[col_name.upper()].iloc[-1]
            return None

        ema_short = get_val(ema_short_col)
        ema_long = get_val(ema_long_col)

        if ema_short is None or ema_long is None:
            logger.warning(f"EMAs not found in DataFrame for {self.timeframe}. Falling back to simple trend detection.")
            is_uptrend = current_price > data['close'].iloc[0]
        else:
            is_uptrend = ema_short > ema_long

        support_levels = []
        resistance_levels = []

        for ratio in self.retracement_ratios:
            level_val = highest_high - (price_range * ratio) if is_uptrend else lowest_low + (price_range * ratio)
            quality = "Strong" if ratio == 0.618 else "Medium"
            name_suffix = f" Support {ratio}" if level_val < current_price else f" Resistance {ratio}"

            level = Level(name=f"Fibonacci{name_suffix}", value=round(level_val, 4),
                          level_type='support' if level_val < current_price else 'resistance', quality=quality)

            if level_val < current_price:
                support_levels.append(level)
            else:
                resistance_levels.append(level)

        for ratio in self.extension_ratios:
            level_val = highest_high + (price_range * ratio) if is_uptrend else lowest_low - (price_range * ratio)
            if level_val > current_price:
                resistance_levels.append(Level(name=f"Fibonacci Extension Resistance {ratio}", value=round(level_val, 4), level_type='resistance', quality='Strong'))
            else:
                support_levels.append(Level(name=f"Fibonacci Extension Support {ratio}", value=round(level_val, 4), level_type='support', quality='Strong'))

        return {
            'supports': sorted(support_levels, key=lambda x: x.value, reverse=True),
            'resistances': sorted(resistance_levels, key=lambda x: x.value)
        }
