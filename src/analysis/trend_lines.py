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
            return {'support_trendline': None, 'resistance_trendline': None, 'price_position': 'N/A'}

        prominence = data['close'].std() * 0.75
        high_pivots_idx, _ = find_peaks(data['high'], prominence=prominence, distance=5)
        low_pivots_idx, _ = find_peaks(-data['low'], prominence=prominence, distance=5)

        support_trend = None
        resistance_trend = None

        if len(low_pivots_idx) >= 2:
            p1_idx, p2_idx = low_pivots_idx[-2], low_pivots_idx[-1]
            p1 = (p1_idx, data['low'].iloc[p1_idx])
            p2 = (p2_idx, data['low'].iloc[p2_idx])
            support_trend = get_line_equation(p1, p2)

        if len(high_pivots_idx) >= 2:
            p1_idx, p2_idx = high_pivots_idx[-2], high_pivots_idx[-1]
            p1 = (p1_idx, data['high'].iloc[p1_idx])
            p2 = (p2_idx, data['high'].iloc[p2_idx])
            resistance_trend = get_line_equation(p1, p2)

        current_price = data['close'].iloc[-1]
        current_time_index = len(data) -1

        support_price = None
        resistance_price = None
        price_position = "N/A"
        score = 0

        if support_trend:
            support_price_at_current_time = support_trend['slope'] * current_time_index + support_trend['intercept']
            if support_price_at_current_time < current_price:
                support_price = support_price_at_current_time
                if current_price > support_price:
                    price_position = "Above Support"
                    score = 10

        if resistance_trend:
            resistance_price_at_current_time = resistance_trend['slope'] * current_time_index + resistance_trend['intercept']
            if resistance_price_at_current_time > current_price:
                resistance_price = resistance_price_at_current_time
                if current_price < resistance_price:
                    price_position = "Below Resistance"
                    if price_position == "Above Support":
                        price_position = "Between Lines"
                    score = -10 if score == 0 else 0


        return {
            'support_trendline_price': support_price,
            'resistance_trendline_price': resistance_price,
            'price_position': price_position,
            'total_score': score
        }
