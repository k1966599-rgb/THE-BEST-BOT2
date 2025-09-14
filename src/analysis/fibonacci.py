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
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_ratios = [1.618, 2.618]

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        if len(df) < self.lookback_period:
            return {'supports': [], 'resistances': []}

        data = df.tail(self.lookback_period)
        highest_high = data['high'].max()
        lowest_low = data['low'].min()
        price_range = highest_high - lowest_low
        logger.info(f"FibonacciAnalysis for {self.timeframe}: Lookback={self.lookback_period}, High={highest_high}, Low={lowest_low}, PriceRange={price_range}")
        if price_range == 0:
            return {'supports': [], 'resistances': []}

        current_price = data['close'].iloc[-1]
        is_uptrend = current_price > data['close'].iloc[0]

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
                 resistances.append(Level(name=f"Fibonacci Extension Resistance {ratio}", value=round(level_val, 4), level_type='resistance', quality='Strong'))
            else:
                 support_levels.append(Level(name=f"Fibonacci Extension Support {ratio}", value=round(level_val, 4), level_type='support', quality='Strong'))

        return {
            'supports': sorted(support_levels, key=lambda x: x.value, reverse=True),
            'resistances': sorted(resistance_levels, key=lambda x: x.value)
        }
