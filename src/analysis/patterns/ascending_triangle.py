import numpy as np
import pandas as pd
from typing import List, Dict
from sklearn.linear_model import LinearRegression

from .base_pattern import BasePattern
from .pattern_utils import cluster_levels
from ..data_models import Pattern

class AscendingTriangle(BasePattern):
    """Detects the Ascending Triangle chart pattern.

    This pattern is characterized by a horizontal resistance line and a rising
    support line, indicating bullish pressure. This class identifies candidates
    for these lines among the provided pivot points.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str, trend_context: dict = None):
        """Initializes the AscendingTriangle pattern detector.

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
        self.name = "المثلث الصاعد"

    def check(self) -> List[Pattern]:
        """Checks for the Ascending Triangle pattern.

        The method identifies a horizontal resistance and a rising support line,
        calculates targets, stop-loss, and a confidence score for any
        valid patterns found.

        Returns:
            List[Pattern]: A list containing the detected Ascending Triangle
            Pattern object, or an empty list if no pattern is found.
        """
        if len(self.highs) < 2 or len(self.lows) < 2:
            return []

        # Cluster the pivot highs to find the horizontal resistance line
        high_prices = [h['price'] for h in self.highs]
        resistance_clusters = cluster_levels(high_prices, self.price_tolerance * 100)

        if not resistance_clusters:
            return []

        # Find the cluster with the most touches, as it's the most significant
        best_res_price = 0
        max_touches = 0
        for cluster_mean in resistance_clusters:
            touches = sum(1 for price in high_prices if abs(price - cluster_mean) / cluster_mean <= self.price_tolerance)
            if touches > max_touches:
                max_touches = touches
                best_res_price = cluster_mean

        if max_touches < 2: # A resistance line needs at least 2 touches
            return []

        # Find rising support line
        support_lows = [l for l in self.lows if l['price'] < best_res_price]
        if len(support_lows) < 2: return []

        support_trend = self.find_trend_line([p['index'] for p in support_lows], [p['price'] for p in support_lows])

        if support_trend['slope'] <= 0: return []

        # Calculate targets and levels
        height = best_res_price - (support_trend['slope'] * support_lows[0]['index'] + support_trend['intercept'])
        if height <= 0: return []

        target1 = best_res_price + height
        target2 = best_res_price + height * 1.618
        stop_loss = support_lows[-1]['price'] * 0.99
        status = 'قيد التكون' if self.current_price < best_res_price else 'نشط'

        # Calculate confidence
        touch_count = len([h for h in self.highs if abs(h['price'] - best_res_price) / best_res_price <= self.price_tolerance]) + len(support_lows)
        volume_analysis = self._analyze_volume(self.highs, support_lows, support_lows[0]['index'])

        confidence = self._calculate_confidence(
            r_squared_upper=1.0, # Horizontal line has perfect R-squared
            r_squared_lower=support_trend['r_squared'],
            touch_count=touch_count,
            volume_confirmation=volume_analysis.get('volume_decline', False),
            pattern_is_bullish=True
        )

        pattern = Pattern(
            name=self.name,
            status=status,
            timeframe=self.timeframe,
            activation_level=round(best_res_price, 4),
            invalidation_level=round(stop_loss, 4),
            target1=round(target1, 4),
            target2=round(target2, 4),
            confidence=confidence
        )
        return [pattern]
