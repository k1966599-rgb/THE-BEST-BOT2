import numpy as np
import pandas as pd
from typing import Dict, List

from .base_pattern import BasePattern

class BullFlag(BasePattern):
    """
    A class for detecting the Bull Flag pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Bull Flag"

    def check(self) -> List[Dict]:
        """
        Checks for the Bull Flag pattern.
        """
        if len(self.highs) < 2 or len(self.lows) < 2:
            return []

        for i in range(len(self.lows) - 1, -1, -1):
            flagpole_start = self.lows[i]
            potential_pole_highs = [h for h in self.highs if h['index'] > flagpole_start['index']]
            if not potential_pole_highs: continue

            flagpole_end = max(potential_pole_highs, key=lambda x: x['price'])
            flagpole_height = flagpole_end['price'] - flagpole_start['price']

            if flagpole_height <= 0: continue

            flag_highs = [h for h in self.highs if h['index'] > flagpole_end['index']]
            flag_lows = [l for l in self.lows if l['index'] > flagpole_end['index']]

            if len(flag_highs) < 2 or len(flag_lows) < 2: continue

            deepest_low = min(flag_lows, key=lambda x: x['price'])['price']
            if (flagpole_end['price'] - deepest_low) / flagpole_height > 0.5:
                continue

            upper_line, lower_line = self._calculate_trend_lines(flag_highs, flag_lows)

            if upper_line['slope'] > 0 or lower_line['slope'] > 0:
                continue

            resistance_current = upper_line['slope'] * (len(self.df) - 1) + upper_line['intercept']

            self.found_patterns.append({
                'name': 'علم صاعد (Bull Flag)',
                'status': 'قيد التكوين 🟡' if self.current_price < resistance_current else 'مكتمل ✅',
                'confidence': 70.0,
                'activation_level': resistance_current,
                'invalidation_level': min([l['price'] for l in flag_lows]),
                'price_target': resistance_current + flagpole_height,
                'stop_loss': min([l['price'] for l in flag_lows]) * 0.99
            })
            if self.found_patterns:
                break

        return self.found_patterns
