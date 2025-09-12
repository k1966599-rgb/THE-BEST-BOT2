import pandas as pd
from typing import Dict, List
from .base_pattern import BasePattern
from ..data_models import Pattern

class RisingWedge(BasePattern):
    """Detects the Rising Wedge chart pattern.

    The Rising Wedge is a bearish pattern that begins wide at the bottom and
    contracts as prices move higher. It is characterized by two converging,
    upward-sloping trend lines.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str, trend_context: dict = None):
        """Initializes the RisingWedge pattern detector.

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
        self.name = "Rising Wedge"

    def check(self) -> List[Pattern]:
        """Checks for the Rising Wedge pattern.

        This method identifies two converging, upward-sloping trend lines,
        validates their quality, and if a pattern is found, calculates targets,
        stop-loss, and a confidence score.

        Returns:
            List[Pattern]: A list containing the detected Rising Wedge
            Pattern object, or an empty list if no pattern is found.
        """
        window_highs, window_lows = self._filter_pivots(search_window_bars=80)
        if len(window_highs) < 3 or len(window_lows) < 3:
            return []

        upper_trend, lower_trend = self._calculate_trend_lines(window_highs, window_lows)

        # Both lines must be upward sloping, and lower must be steeper (converging)
        if not (upper_trend['slope'] > 0 and lower_trend['slope'] > 0 and lower_trend['slope'] > upper_trend['slope']):
            return []

        if upper_trend['r_squared'] < 0.6 or lower_trend['r_squared'] < 0.6:
            return []

        activation_level = lower_trend['slope'] * (len(self.df) - 1) + lower_trend['intercept']
        stop_loss = max([h['price'] for h in window_highs]) * 1.01
        wedge_height = max([p['price'] for p in window_highs]) - min([p['price'] for p in window_lows])

        target1 = activation_level - wedge_height
        target2 = activation_level - wedge_height * 1.618

        volume_analysis = self._analyze_volume(window_highs, window_lows, window_highs[0]['index'])
        confidence = self._calculate_confidence(
            r_squared_upper=upper_trend['r_squared'],
            r_squared_lower=lower_trend['r_squared'],
            touch_count=len(window_highs) + len(window_lows),
            volume_confirmation=volume_analysis.get('volume_decline', False),
            pattern_is_bullish=False
        )

        pattern = Pattern(
            name='وتد صاعد',
            status='قيد التكوين' if self.current_price > activation_level else 'مفعل',
            timeframe=self.timeframe,
            activation_level=round(activation_level, 4),
            invalidation_level=round(stop_loss, 4),
            target1=round(target1, 4),
            target2=round(target2, 4),
            confidence=confidence
        )
        return [pattern]
