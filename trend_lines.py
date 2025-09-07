import pandas as pd
from scipy.signal import find_peaks
from typing import Dict, Any, Optional

def get_line_equation(p1: tuple, p2: tuple) -> Optional[Dict[str, float]]:
    """Calculates the slope and intercept of a line given two points."""
    x1, y1 = p1
    x2, y2 = p2
    if x2 == x1: return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return {'slope': slope, 'intercept': intercept}

class TrendLineAnalysis:
    def __init__(self, df: pd.DataFrame, config: dict = None):
        self.df = df.copy()
        if config is None: config = {}
        self.config = config
        self.long_period = config.get('TREND_LONG_PERIOD', 100)

    def get_comprehensive_trend_lines_analysis(self) -> Dict[str, Any]:
        """
        Finds the most recent major uptrend and downtrend lines and provides a basic analysis.
        """
        data = self.df.tail(self.long_period)
        if len(data) < 20:
            return {'uptrend': None, 'downtrend': None, 'price_position': 'N/A'}

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

        # Basic analysis of price position relative to trend lines
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
