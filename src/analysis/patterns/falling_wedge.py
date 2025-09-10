import pandas as pd
from typing import Dict, List
from .base_pattern import BasePattern
from ..data_models import Pattern

class FallingWedge(BasePattern):
    """
    A class for detecting the Falling Wedge pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Falling Wedge"
        self.timeframe = timeframe

    def check(self) -> List[Pattern]:
        """
        Checks for the Falling Wedge pattern.
        """
        window_highs, window_lows = self._filter_pivots(search_window_bars=80)
        if len(window_highs) < 3 or len(window_lows) < 3:
            return []

        upper_trend, lower_trend = self._calculate_trend_lines(window_highs, window_lows)

        # Both lines must be downward sloping, and the support line must be less steep (converging)
        if not (upper_trend['slope'] < 0 and lower_trend['slope'] < 0 and upper_trend['slope'] < lower_trend['slope']):
            return []

        # R-squared check for line quality
        if upper_trend['r_squared'] < 0.6 or lower_trend['r_squared'] < 0.6:
            return []

        activation_level = upper_trend['slope'] * (len(self.df) - 1) + upper_trend['intercept']
        stop_loss = min([l['price'] for l in window_lows]) * 0.99
        wedge_height = max([p['price'] for p in window_highs]) - min([p['price'] for p in window_lows])

        target1 = activation_level + wedge_height
        target2 = activation_level + wedge_height * 1.618

        confidence = self._calculate_confidence(
            r_squared_upper=upper_trend['r_squared'],
            r_squared_lower=lower_trend['r_squared'],
            touch_count=len(window_highs) + len(window_lows)
        )

        pattern = Pattern(
            name='وتد هابط',
            status='قيد التكوين' if self.current_price < activation_level else 'مفعل',
            timeframe=self.timeframe,
            activation_level=round(activation_level, 4),
            invalidation_level=round(stop_loss, 4),
            target1=round(target1, 4),
            target2=round(target2, 4),
            confidence=confidence
        )
        return [pattern]
