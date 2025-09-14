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
    highs = [{'index': df.index[i], 'price': df.iloc[i]['high']} for i in high_pivots_idx]
    lows = [{'index': df.index[i], 'price': df.iloc[i]['low']} for i in low_pivots_idx]
    return highs, lows

def cluster_levels(levels: List[float], tolerance: float = 0.5) -> List[float]:
    """
    Groups close price levels together into clusters and returns the mean of each cluster.

    Args:
        levels (List[float]): A list of price levels to cluster.
        tolerance (float): The percentage difference allowed to form a cluster.

    Returns:
        List[float]: A list containing the mean value of each identified cluster.
    """
    if not levels:
        return []

    levels.sort()

    clusters = []
    if not levels:
        return clusters

    current_cluster = [levels[0]]

    for i in range(1, len(levels)):
        # Compare with the last item in the current cluster
        if (levels[i] - current_cluster[-1]) / current_cluster[-1] * 100 <= tolerance:
            current_cluster.append(levels[i])
        else:
            clusters.append(np.mean(current_cluster))
            current_cluster = [levels[i]]

    if current_cluster:
        clusters.append(np.mean(current_cluster))

    return clusters
