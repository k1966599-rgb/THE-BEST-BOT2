import numpy as np
import pandas as pd
from typing import Dict, List

from .base_pattern import BasePattern

class DoubleBottom(BasePattern):
    """
    A class for detecting the Double Bottom pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Double Bottom"

    def check(self) -> List[Dict]:
        """
        Checks for the Double Bottom pattern.
        """
        if len(self.lows) < 2 or len(self.highs) < 1:
            return []

        for i in range(len(self.lows) - 1):
            for j in range(i + 1, len(self.lows)):
                bottom1 = self.lows[i]
                bottom2 = self.lows[j]

                if abs(bottom1['price'] - bottom2['price']) / bottom1['price'] > self.price_tolerance:
                    continue

                intervening_highs = [h for h in self.highs if bottom1['index'] < h['index'] < bottom2['index']]
                if not intervening_highs:
                    continue

                neckline = max(intervening_highs, key=lambda x: x['price'])
                neckline_price = neckline['price']

                if bottom1['price'] >= neckline_price or bottom2['price'] >= neckline_price:
                    continue

                height = neckline_price - np.mean([bottom1['price'], bottom2['price']])
                target = neckline_price + height
                stop_loss = min(bottom1['price'], bottom2['price']) * 0.99

                self.found_patterns.append({
                    'name': 'قاع مزدوج (Double Bottom)',
                    'status': 'قيد التكوين 🟡' if self.current_price < neckline_price else 'مكتمل ✅',
                    'confidence': 70.0,
                    'activation_level': neckline_price,
                    'invalidation_level': min(bottom1['price'], bottom2['price']),
                    'price_target': target,
                    'stop_loss': stop_loss
                })
                if self.found_patterns:
                    return self.found_patterns

        return self.found_patterns
