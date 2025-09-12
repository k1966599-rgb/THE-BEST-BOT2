import numpy as np
import pandas as pd
from typing import Dict, List
from scipy.signal import find_peaks

def get_pivots(df: pd.DataFrame, order: int = 5) -> (List[Dict], List[Dict]):
    """Detects pivot high and low points in a DataFrame.

    This function uses `scipy.signal.find_peaks` to identify local maxima
    in the 'high' column and local minima in the 'low' column of the
    provided DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame containing market data with 'high'
            and 'low' columns.
        order (int, optional): The minimum number of bars between adjacent
            pivots. Defaults to 5.

    Returns:
        tuple: A tuple containing two lists:
        - A list of pivot high dictionaries, each with 'index' and 'price'.
        - A list of pivot low dictionaries, each with 'index' and 'price'.
    """
    high_pivots_idx, _ = find_peaks(df['high'], distance=order, prominence=df['high'].std() * 0.5)
    low_pivots_idx, _ = find_peaks(-df['low'], distance=order, prominence=df['low'].std() * 0.5)
    highs = [{'index': i, 'price': df.iloc[i]['high']} for i in high_pivots_idx]
    lows = [{'index': i, 'price': df.iloc[i]['low']} for i in low_pivots_idx]
    return highs, lows
