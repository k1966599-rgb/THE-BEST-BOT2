import pandas as pd
import numpy as np
from typing import Dict, List
from .base_analysis import BaseAnalysis
from .data_models import Level

class FibonacciAnalysis(BaseAnalysis):
    """Performs Fibonacci analysis to find support and resistance levels.

    This class identifies the highest high and lowest low over a lookback
    period to calculate Fibonacci retracement and extension levels. These
    levels are potential areas of support and resistance.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        """Initializes the FibonacciAnalysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed. Defaults to '1h'.
        """
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback_period = overrides.get('FIB_LOOKBACK', self.config.get('FIB_LOOKBACK', 90))
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_ratios = [1.618, 2.618]

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """Calculates Fibonacci retracement and extension levels.

        This method determines the trend within the lookback period and then
        calculates potential support and resistance levels based on Fibonacci
        ratios.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.

        Returns:
            Dict[str, List[Level]]: A dictionary containing lists of support
            and resistance Level objects, sorted by price. Returns empty
            lists if the data is insufficient.
        """
        if len(df) < self.lookback_period:
            return {'supports': [], 'resistances': []}

        data = df.tail(self.lookback_period)
        highest_high = data['high'].max()
        lowest_low = data['low'].min()
        price_range = highest_high - lowest_low
        if price_range == 0:
            return {'supports': [], 'resistances': []}

        current_price = data['close'].iloc[-1]
        is_uptrend = current_price > data['close'].iloc[0]

        support_levels = []
        resistance_levels = []

        # Calculate Retracement Levels
        for ratio in self.retracement_ratios:
            level_val = highest_high - (price_range * ratio) if is_uptrend else lowest_low + (price_range * ratio)
            level_val = round(level_val, 4)
            quality = "قوي" if ratio == 0.618 else "متوسط"

            if level_val < current_price:
                support_levels.append(Level(name=f"دعم فيبو {ratio}", value=level_val, level_type='support', quality=quality))
            else:
                resistance_levels.append(Level(name=f"مقاومة فيبو {ratio}", value=level_val, level_type='resistance', quality=quality))

        # Calculate Extension Levels (as potential future targets/resistances or supports)
        for ratio in self.extension_ratios:
            level_val = highest_high + (price_range * ratio) if is_uptrend else lowest_low - (price_range * ratio)
            level_val = round(level_val, 4)

            if level_val > current_price:
                 resistance_levels.append(Level(name=f"مقاومة فيبو امتداد {ratio}", value=level_val, level_type='resistance', quality='قوية'))
            else:
                 support_levels.append(Level(name=f"دعم فيبو امتداد {ratio}", value=level_val, level_type='support', quality='قوي'))

        return {
            'supports': sorted(support_levels, key=lambda x: x.value, reverse=True),
            'resistances': sorted(resistance_levels, key=lambda x: x.value)
        }
