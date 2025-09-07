import pandas as pd
from scipy.signal import find_peaks
from typing import Dict, Any, Optional
from .base_analysis import BaseAnalysis

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

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        data = df.tail(self.long_period)
        if len(data) < 20:
            return {'uptrend': None, 'downtrend': None, 'price_position': 'N/A'}
        # ... rest of the logic using `data` instead of `self.df`
        prominence = data['Close'].std() * 0.75
        high_pivots_idx, _ = find_peaks(data['High'], prominence=prominence, distance=5)
        low_pivots_idx, _ = find_peaks(-data['Low'], prominence=prominence, distance=5)
        uptrend_line, downtrend_line = None, None
        if len(low_pivots_idx) >= 2:
            p1_idx, p2_idx = low_pivots_idx[-2], low_pivots_idx[-1]
            p1 = (p1_idx, data['Low'].iloc[p1_idx])
            p2 = (p2_idx, data['Low'].iloc[p2_idx])
            uptrend_line = get_line_equation(p1, p2)
        if len(high_pivots_idx) >= 2:
            p1_idx, p2_idx = high_pivots_idx[-2], high_pivots_idx[-1]
            p1 = (p1_idx, data['High'].iloc[p1_idx])
            p2 = (p2_idx, data['High'].iloc[p2_idx])
            downtrend_line = get_line_equation(p1, p2)
        price_position = "N/A"
        current_price = data['Close'].iloc[-1]
        if uptrend_line:
            trend_line_price_at_current_time = uptrend_line['slope'] * len(data) + uptrend_line['intercept']
            if current_price > trend_line_price_at_current_time:
                price_position = "Above Uptrend"
        if downtrend_line:
            trend_line_price_at_current_time = downtrend_line['slope'] * len(data) + downtrend_line['intercept']
            if current_price < trend_line_price_at_current_time:
                price_position = "Below Downtrend"
        return {
            'uptrend': uptrend_line,
            'downtrend': downtrend_line,
            'price_position': price_position
        }
