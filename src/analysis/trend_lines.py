import pandas as pd
from scipy.signal import find_peaks
from typing import Dict, Any, Optional, List
from .base_analysis import BaseAnalysis
from .data_models import Level

def get_line_equation(p1: tuple, p2: tuple) -> Optional[Dict[str, float]]:
    """Calculates the slope and intercept of a line defined by two points.

    Args:
        p1 (tuple): The first point (x1, y1).
        p2 (tuple): The second point (x2, y2).

    Returns:
        Optional[Dict[str, float]]: A dictionary with 'slope' and 'intercept',
        or None if the line is vertical.
    """
    x1, y1 = p1
    x2, y2 = p2
    if x2 == x1: return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return {'slope': slope, 'intercept': intercept}

class TrendLineAnalysis(BaseAnalysis):
    """Analyzes and identifies trend lines from price data.

    This class finds recent pivot highs and lows to construct support and
    resistance trend lines, then projects them to the current time to act as
    dynamic levels.
    """
    def __init__(self, config: dict = None, timeframe: str = None):
        """Initializes the TrendLineAnalysis module.

        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
            timeframe (str, optional): The timeframe for analysis. Defaults to None.
        """
        super().__init__(config, timeframe)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)

    def _get_pivots(self, data: pd.DataFrame) -> (list, list):
        """Identifies pivot high and low points in the data.

        Args:
            data (pd.DataFrame): The input price data.

        Returns:
            tuple: A tuple containing two lists: indices of high pivots and
            indices of low pivots.
        """
        prominence = data['close'].std() * 0.4 # Reduced for more sensitivity
        high_pivots_idx, _ = find_peaks(data['high'], prominence=prominence, distance=5)
        low_pivots_idx, _ = find_peaks(-data['low'], prominence=prominence, distance=5)
        return high_pivots_idx, low_pivots_idx

    def _get_trend_lines(self, data: pd.DataFrame, high_pivots_idx: list, low_pivots_idx: list) -> (dict, dict):
        """Constructs trend lines from the last two pivot points.

        Args:
            data (pd.DataFrame): The input price data.
            high_pivots_idx (list): Indices of high pivots.
            low_pivots_idx (list): Indices of low pivots.

        Returns:
            tuple: A tuple containing two dictionaries: one for the support
            trend line equation and one for the resistance trend line equation.
            Can be None if not enough pivots are found.
        """
        support_trend, resistance_trend = None, None
        if len(low_pivots_idx) >= 2:
            p1_idx, p2_idx = low_pivots_idx[-2], low_pivots_idx[-1]
            p1_x_val = data.index[p1_idx]
            if pd.api.types.is_datetime64_any_dtype(data.index):
                p1_x = data.index[p1_idx].value
                p2_x = data.index[p2_idx].value
            else:
                p1_x = data.index[p1_idx]
                p2_x = data.index[p2_idx]
            support_trend = get_line_equation((p1_x, data['low'].iloc[p1_idx]), (p2_x, data['low'].iloc[p2_idx]))
        if len(high_pivots_idx) >= 2:
            p1_idx, p2_idx = high_pivots_idx[-2], high_pivots_idx[-1]
            if pd.api.types.is_datetime64_any_dtype(data.index):
                p1_x = data.index[p1_idx].value
                p2_x = data.index[p2_idx].value
            else:
                p1_x = data.index[p1_idx]
                p2_x = data.index[p2_idx]
            resistance_trend = get_line_equation((p1_x, data['high'].iloc[p1_idx]), (p2_x, data['high'].iloc[p2_idx]))
        return support_trend, resistance_trend

    def _get_trend_name(self) -> str:
        """Returns the trend name based on the timeframe."""
        if self.timeframe == '1d':
            return "طويل المدى"
        if self.timeframe == '4h':
            return "متوسط المدى"
        return "قصير المدى"

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """Identifies dynamic support and resistance levels from trend lines.

        This method orchestrates the process of finding pivots, creating trend
        lines, and then calculating the current price levels of these lines to
        serve as dynamic support and resistance.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.

        Returns:
            Dict[str, List[Level]]: A dictionary containing lists of support
            and resistance Level objects derived from the trend lines.
        """
        data = df.tail(self.long_period)
        if len(data) < 20:
            return {'supports': [], 'resistances': []}

        high_pivots_idx, low_pivots_idx = self._get_pivots(data)
        logger.info(f"TrendLineAnalysis for {self.timeframe}: Found {len(low_pivots_idx)} low pivots and {len(high_pivots_idx)} high pivots. Need at least 2 of each to draw a line.")
        support_trend, resistance_trend = self._get_trend_lines(data, high_pivots_idx, low_pivots_idx)

        supports = []
        resistances = []
        current_price = data['close'].iloc[-1]
        if pd.api.types.is_datetime64_any_dtype(data.index):
            current_time_x = data.index[-1].value
        else:
            current_time_x = data.index[-1]

        if support_trend:
            support_price = support_trend['slope'] * current_time_x + support_trend['intercept']
            if support_price < current_price:
                trend_name = self._get_trend_name()
                supports.append(Level(name=f"دعم الاتجاه {trend_name}", value=round(support_price, 4), level_type='support', quality='حرج'))

        if resistance_trend:
            resistance_price = resistance_trend['slope'] * current_time_x + resistance_trend['intercept']
            if resistance_price > current_price:
                trend_name = self._get_trend_name()
                resistances.append(Level(name=f"مقاومة الاتجاه {trend_name}", value=round(resistance_price, 4), level_type='resistance', quality='حرج'))

        return {'supports': supports, 'resistances': resistances}
