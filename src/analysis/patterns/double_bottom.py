import numpy as np
import pandas as pd
from typing import Dict, List

from .base_pattern import BasePattern
from ..data_models import Pattern

class DoubleBottom(BasePattern):
    """
    A class for detecting the Double Bottom pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Double Bottom"
        self.timeframe = timeframe

    def check(self) -> List[Pattern]:
        """
        Checks for the Double Bottom pattern.
        """
        if len(self.lows) < 2 or len(self.highs) < 1: return []

        for i in range(len(self.lows) - 1):
            for j in range(i + 1, len(self.lows)):
                bottom1, bottom2 = self.lows[i], self.lows[j]
                if abs(bottom1['price'] - bottom2['price']) / bottom1['price'] > self.price_tolerance: continue

                intervening_highs = [h for h in self.highs if bottom1['index'] < h['index'] < bottom2['index']]
                if not intervening_highs: continue

                neckline = max(intervening_highs, key=lambda x: x['price'])
                neckline_price = neckline['price']
                if bottom1['price'] >= neckline_price or bottom2['price'] >= neckline_price: continue

                height = neckline_price - np.mean([bottom1['price'], bottom2['price']])
                if height <= 0: continue

                target1 = neckline_price + height
                target2 = neckline_price + height * 1.618
                stop_loss = min(bottom1['price'], bottom2['price'])

                confidence = self._calculate_confidence(touch_count=len(intervening_highs) + 2)

                pattern = Pattern(
                    name='قاع مزدوج',
                    status='قيد التكوين' if self.current_price < neckline_price else 'مفعل',
                    timeframe=self.timeframe,
                    activation_level=round(neckline_price, 4),
                    invalidation_level=round(stop_loss, 4),
                    target1=round(target1, 4),
                    target2=round(target2, 4),
                    confidence=confidence
                )
                return [pattern]

        return []
