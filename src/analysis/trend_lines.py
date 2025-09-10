import pandas as pd
from scipy.signal import find_peaks
from typing import Dict, Any, Optional, List
from .base_analysis import BaseAnalysis
from .data_models import Level

def get_line_equation(p1: tuple, p2: tuple) -> Optional[Dict[str, float]]:
    x1, y1 = p1
    x2, y2 = p2
    if x2 == x1: return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return {'slope': slope, 'intercept': intercept}

class TrendLineAnalysis(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = None):
        super().__init__(config, timeframe)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)

    def _get_pivots(self, data: pd.DataFrame) -> (list, list):
        prominence = data['close'].std() * 0.75
        high_pivots_idx, _ = find_peaks(data['high'], prominence=prominence, distance=5)
        low_pivots_idx, _ = find_peaks(-data['low'], prominence=prominence, distance=5)
        return high_pivots_idx, low_pivots_idx

    def _get_trend_lines(self, data: pd.DataFrame, high_pivots_idx: list, low_pivots_idx: list) -> (dict, dict):
        support_trend, resistance_trend = None, None
        if len(low_pivots_idx) >= 2:
            p1_idx, p2_idx = low_pivots_idx[-2], low_pivots_idx[-1]
            support_trend = get_line_equation((p1_idx, data['low'].iloc[p1_idx]), (p2_idx, data['low'].iloc[p2_idx]))
        if len(high_pivots_idx) >= 2:
            p1_idx, p2_idx = high_pivots_idx[-2], high_pivots_idx[-1]
            resistance_trend = get_line_equation((p1_idx, data['high'].iloc[p1_idx]), (p2_idx, data['high'].iloc[p2_idx]))
        return support_trend, resistance_trend

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        data = df.tail(self.long_period)
        if len(data) < 20:
            return {'supports': [], 'resistances': []}

        high_pivots_idx, low_pivots_idx = self._get_pivots(data)
        support_trend, resistance_trend = self._get_trend_lines(data, high_pivots_idx, low_pivots_idx)

        supports = []
        resistances = []
        current_price = data['close'].iloc[-1]
        current_time_index = len(data) - 1

        if support_trend:
            support_price = support_trend['slope'] * current_time_index + support_trend['intercept']
            if support_price < current_price:
                supports.append(Level(name="دعم ترند قصير", value=round(support_price, 4), level_type='support', quality='حرج'))

        if resistance_trend:
            resistance_price = resistance_trend['slope'] * current_time_index + resistance_trend['intercept']
            if resistance_price > current_price:
                resistances.append(Level(name="مقاومة ترند قصير", value=round(resistance_price, 4), level_type='resistance', quality='حرج'))

        return {'supports': supports, 'resistances': resistances}
