import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Any

def find_new_support_resistance(df: pd.DataFrame, prominence: float = 0.02, width: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identifies support and resistance levels with qualitative descriptions.
    Uses peak/trough analysis and clustering to determine level strength.

    Args:
        df: A pandas DataFrame with 'high', 'low', and 'close' columns.
        prominence: The required prominence of peaks. This is a fraction of the price range.
        width: The required width of peaks in number of samples.

    Returns:
        A dictionary containing 'supports' and 'resistances', with lists of dictionaries.
        Each dictionary has 'level' (float) and 'description' (str).
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

    # --- Level Clustering to determine strength ---
    all_levels = sorted(list(set(supports + resistances)))
    clustered_levels = []
    if all_levels:
        current_cluster = [all_levels[0]]
        for level in all_levels[1:]:
            # Cluster levels within 1% of each other
            if level <= np.mean(current_cluster) * 1.01:
                current_cluster.append(level)
            else:
                # Store the mean of the cluster and its size (strength)
                clustered_levels.append({'level': np.mean(current_cluster), 'strength': len(current_cluster)})
                current_cluster = [level]
        clustered_levels.append({'level': np.mean(current_cluster), 'strength': len(current_cluster)})

    # --- Separate clustered levels and assign descriptions ---
    final_supports = []
    final_resistances = []
    last_close = df['close'].iloc[-1]

    for data in clustered_levels:
        level = round(data['level'], 4)
        strength = data['strength']
        if level < last_close:
            final_supports.append({'level': level, 'strength': strength})
        else:
            final_resistances.append({'level': level, 'strength': strength})

    # Sort supports descending (closest first) and resistances ascending (closest first)
    final_supports = sorted(final_supports, key=lambda x: x['level'], reverse=True)
    final_resistances = sorted(final_resistances, key=lambda x: x['level'])

    # Assign qualitative descriptions
    for i, sup in enumerate(final_supports):
        if i == 0:
            sup['description'] = "دعم حرج"
        elif sup['strength'] >= 3:
            sup['description'] = "دعم قوي"
        else:
            sup['description'] = "دعم ثانوي"

    for i, res in enumerate(final_resistances):
        if i == 0:
            res['description'] = "مقاومة حرجة"
        elif res['strength'] >= 3:
            res['description'] = "مقاومة قوية"
        else:
            res['description'] = "مقاومة ثانوية"

    # Add historical levels
    historical_low = df['low'].min()
    historical_high = df['high'].max()
    final_supports.append({'level': historical_low, 'description': 'دعم تاريخي', 'strength': 99})
    final_resistances.append({'level': historical_high, 'description': 'مقاومة تاريخية', 'strength': 99})

    # Remove duplicates that might have been added
    final_supports = [dict(t) for t in {tuple(d.items()) for d in final_supports}]
    final_resistances = [dict(t) for t in {tuple(d.items()) for d in final_resistances}]

    # Sort again and take the top 5 closest
    final_supports = sorted(final_supports, key=lambda x: x['level'], reverse=True)[:5]
    final_resistances = sorted(final_resistances, key=lambda x: x['level'])[:5]


    return {
        'supports': final_supports,
        'resistances': final_resistances
    }
