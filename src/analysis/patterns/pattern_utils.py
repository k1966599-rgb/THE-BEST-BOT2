import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.linear_model import LinearRegression

# This file will contain all helper functions for pattern detection.

def get_pivots(df: pd.DataFrame, order: int = 5) -> (List[Dict], List[Dict]):
    """Detects pivot high and low points in a DataFrame."""
    from scipy.signal import find_peaks
    high_pivots_idx, _ = find_peaks(df['high'], distance=order, prominence=df['high'].std() * 0.5)
    low_pivots_idx, _ = find_peaks(-df['low'], distance=order, prominence=df['low'].std() * 0.5)
    highs = [{'index': i, 'price': df.iloc[i]['high']} for i in high_pivots_idx]
    lows = [{'index': i, 'price': df.iloc[i]['low']} for i in low_pivots_idx]
    return highs, lows

def calculate_dynamic_confidence(df: pd.DataFrame, base_confidence: float = 70) -> float:
    """Calculates a dynamic confidence score based on market conditions."""
    confidence = base_confidence
    if 'volume' in df.columns and len(df) > 20:
        recent_volume = df['volume'].tail(10).mean()
        avg_volume = df['volume'].mean()
        if recent_volume > avg_volume * 1.2:
            confidence += 10
    volatility = df['close'].pct_change().tail(20).std()
    if 0.01 < volatility < 0.03:
        confidence += 5
    elif volatility > 0.05:
        confidence -= 10
    return min(95, max(30, confidence))

def find_trend_line(x_values: List[int], y_values: List[float]) -> Dict:
    """إيجاد خط الاتجاه باستخدام الانحدار الخطي"""
    if len(x_values) < 2 or len(y_values) < 2:
        return {'slope': 0, 'intercept': 0, 'r_squared': 0}

    x_array = np.array(x_values).reshape(-1, 1)
    y_array = np.array(y_values)

    reg = LinearRegression().fit(x_array, y_array)
    r_squared = reg.score(x_array, y_array)

    return {
        'slope': reg.coef_[0],
        'intercept': reg.intercept_,
        'r_squared': r_squared
    }
