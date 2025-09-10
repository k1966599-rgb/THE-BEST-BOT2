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

# This file will contain all helper functions for pattern detection.
