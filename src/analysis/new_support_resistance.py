import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List

def find_new_support_resistance(df: pd.DataFrame, prominence: float = 0.02, width: int = 10) -> Dict[str, List[float]]:
    """
    Identifies support and resistance levels from historical price data using peak/trough analysis.
    This is the new, real implementation.

    Args:
        df: A pandas DataFrame with 'high', 'low', and 'close' columns.
        prominence: The required prominence of peaks. This is a fraction of the price range.
        width: The required width of peaks in number of samples.

    Returns:
        A dictionary containing two keys, 'supports' and 'resistances', with lists of price levels.
    """
    if df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        return {'supports': [], 'resistances': []}

    price_range = df['high'].max() - df['low'].min()
    if price_range == 0:
        return {'supports': [], 'resistances': []}

    prominence_value = price_range * prominence

    # Find peaks for resistance
    resistance_indices, _ = find_peaks(df['high'], prominence=prominence_value, width=width)
    resistances = df['high'].iloc[resistance_indices].to_list()

    # Find troughs for support
    support_indices, _ = find_peaks(-df['low'], prominence=prominence_value, width=width)
    supports = df['low'].iloc[support_indices].to_list()

    # --- Level Clustering to reduce noise ---
    all_levels = sorted(list(set(supports + resistances)))
    clustered_levels = []
    if all_levels:
        current_cluster = [all_levels[0]]
        # Cluster levels that are within 1% of each other
        for level in all_levels[1:]:
            if level <= np.mean(current_cluster) * 1.01:
                current_cluster.append(level)
            else:
                clustered_levels.append(np.mean(current_cluster))
                current_cluster = [level]
        clustered_levels.append(np.mean(current_cluster))

    # --- Separate clustered levels back into support and resistance ---
    final_supports = []
    final_resistances = []
    last_close = df['close'].iloc[-1]

    for level in clustered_levels:
        if level < last_close:
            final_supports.append(round(level, 4))
        else:
            final_resistances.append(round(level, 4))

    # Fallback if clustering removes all levels of one type
    if not final_supports and supports:
        final_supports = [round(s, 4) for s in sorted(list(set(supports))) if s < last_close]
    if not final_resistances and resistances:
        final_resistances = [round(r, 4) for r in sorted(list(set(resistances))) if r > last_close]

    return {
        'supports': sorted(list(set(final_supports)), reverse=True)[:5],  # Top 5 closest
        'resistances': sorted(list(set(final_resistances)))[:5] # Top 5 closest
    }
