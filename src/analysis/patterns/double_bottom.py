import numpy as np
import pandas as pd
from typing import Dict, List

from .base_pattern import BasePattern
from ..data_models import Pattern

class DoubleBottom(BasePattern):
    """Detects the Double Bottom chart pattern.

    This bullish reversal pattern is characterized by two consecutive troughs
    at roughly the same price level, separated by a peak (the neckline). It
    often resembles the letter "W".
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str, trend_context: dict = None):
        """Initializes the DoubleBottom pattern detector.

        Args:
            df (pd.DataFrame): The market data.
            config (dict): Configuration settings.
            highs (List[Dict]): List of pivot high points.
            lows (List[Dict]): List of pivot low points.
            current_price (float): The current market price.
            price_tolerance (float): The tolerance for price comparisons.
            timeframe (str): The timeframe of the data.
            trend_context (dict, optional): Context about the preceding trend.
                Defaults to None.
        """
        super().__init__(df, config, highs, lows, current_price, price_tolerance, timeframe, trend_context)
        self.name = "Double Bottom"

    def check(self) -> List[Pattern]:
        """Checks for the Double Bottom pattern.

        This method searches for two similar lows separated by a significant
        high (neckline). If found, it calculates targets, stop-loss, and a
        confidence score.

        Returns:
            List[Pattern]: A list containing the detected Double Bottom
            Pattern object, or an empty list if no pattern is found.
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

                volume_analysis = self._analyze_volume(intervening_highs, [bottom1, bottom2], bottom1['index'])
                confidence = self._calculate_confidence(
                    touch_count=len(intervening_highs) + 2,
                    volume_confirmation=volume_analysis.get('volume_decline', False),
                    pattern_is_bullish=True
                )

                pattern = Pattern(
                    name='Double Bottom',
                    status='Forming' if self.current_price < neckline_price else 'Active',
                    timeframe=self.timeframe,
                    activation_level=round(neckline_price, 4),
                    invalidation_level=round(stop_loss, 4),
                    target1=round(target1, 4),
                    target2=round(target2, 4),
                    confidence=confidence
                )
                return [pattern]

        return []
