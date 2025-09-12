import pandas as pd
from typing import Dict, List
from .base_pattern import BasePattern
from ..data_models import Pattern

class BearFlag(BasePattern):
    """Detects the Bear Flag chart pattern.

    A Bear Flag is a bearish continuation pattern characterized by a sharp
    decline (the flagpole) followed by a brief, upward-sloping consolidation
    channel (the flag).
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str, trend_context: dict = None):
        """Initializes the BearFlag pattern detector.

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
        self.name = "علم هابط"

    def check(self) -> List[Pattern]:
        """Checks for the Bear Flag pattern.

        This method iterates through historical pivots to find a flagpole,
        followed by a consolidation flag with the correct characteristics.
        It calculates targets, stop-loss, and a confidence score.

        Returns:
            List[Pattern]: A list containing the detected Bear Flag Pattern
            object, or an empty list if no pattern is found.
        """
        if len(self.highs) < 3: return []

        for i in range(len(self.highs) - 2, 0, -1):
            # Find flagpole
            flagpole_start = self.highs[i-1]
            flagpole_end = min([l for l in self.lows if l['index'] > flagpole_start['index'] and l['index'] < self.highs[i]['index']], default=None, key=lambda x: x['price'])
            if not flagpole_end: continue

            flagpole_height = flagpole_start['price'] - flagpole_end['price']
            if flagpole_height <= 0: continue

            # Find flag
            flag_highs = [h for h in self.highs if h['index'] > flagpole_end['index']]
            flag_lows = [l for l in self.lows if l['index'] > flagpole_end['index']]
            if len(flag_highs) < 2 or len(flag_lows) < 2: continue

            # Check retracement
            highest_high = max(flag_highs, key=lambda x: x['price'])['price']
            if (highest_high - flagpole_end['price']) / flagpole_height > 0.5: continue

            # Check for parallel upward trendlines for the flag
            upper_line, lower_line = self._calculate_trend_lines(flag_highs, flag_lows)
            if upper_line['slope'] < 0 or lower_line['slope'] < 0: continue

            activation_level = lower_line['slope'] * (len(self.df) - 1) + lower_line['intercept']
            stop_loss = max([h['price'] for h in flag_highs]) * 1.01

            target1 = activation_level - flagpole_height
            target2 = activation_level - flagpole_height * 1.618

            volume_analysis = self._analyze_volume(flag_highs, flag_lows, flagpole_end['index'])
            confidence = self._calculate_confidence(
                r_squared_upper=upper_line['r_squared'],
                r_squared_lower=lower_line['r_squared'],
                touch_count=len(flag_highs) + len(flag_lows),
                volume_confirmation=volume_analysis.get('volume_decline', False),
                pattern_is_bullish=False
            )

            pattern = Pattern(
                name=self.name,
                status='قيد التكون' if self.current_price > activation_level else 'نشط',
                timeframe=self.timeframe,
                activation_level=round(activation_level, 4),
                invalidation_level=round(stop_loss, 4),
                target1=round(target1, 4),
                target2=round(target2, 4),
                confidence=confidence
            )
            return [pattern]

        return []
