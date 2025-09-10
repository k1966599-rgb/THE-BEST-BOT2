import numpy as np
import pandas as pd
from typing import Dict, List

from .base_pattern import BasePattern
from ..data_models import Pattern

class BullFlag(BasePattern):
    """
    A class for detecting the Bull Flag pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Bull Flag"
        self.timeframe = timeframe

    def check(self) -> List[Pattern]:
        """
        Checks for the Bull Flag pattern.
        """
        if len(self.lows) < 3: return []

        for i in range(len(self.lows) - 2, 0, -1):
            # Find flagpole
            flagpole_start = self.lows[i-1]
            flagpole_end = max([h for h in self.highs if h['index'] > flagpole_start['index'] and h['index'] < self.lows[i]['index']], default=None, key=lambda x: x['price'])
            if not flagpole_end: continue

            flagpole_height = flagpole_end['price'] - flagpole_start['price']
            if flagpole_height <= 0: continue

            # Find flag
            flag_highs = [h for h in self.highs if h['index'] > flagpole_end['index']]
            flag_lows = [l for l in self.lows if l['index'] > flagpole_end['index']]
            if len(flag_highs) < 2 or len(flag_lows) < 2: continue

            # Check retracement
            deepest_low = min(flag_lows, key=lambda x: x['price'])['price']
            if (flagpole_end['price'] - deepest_low) / flagpole_height > 0.5: continue

            # Check for parallel downward trendlines for the flag
            upper_line, lower_line = self._calculate_trend_lines(flag_highs, flag_lows)
            if upper_line['slope'] > 0 or lower_line['slope'] > 0: continue

            activation_level = upper_line['slope'] * (len(self.df) - 1) + upper_line['intercept']
            stop_loss = min([l['price'] for l in flag_lows]) * 0.99

            target1 = activation_level + flagpole_height
            target2 = activation_level + flagpole_height * 1.618

            pattern = Pattern(
                name='علم صاعد',
                status='قيد التكوين' if self.current_price < activation_level else 'مفعل',
                timeframe=self.timeframe,
                activation_level=round(activation_level, 4),
                invalidation_level=round(stop_loss, 4),
                target1=round(target1, 4),
                target2=round(target2, 4)
            )
            return [pattern] # Return the first one found

        return []
