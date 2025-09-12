import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List
from .data_models import Level

def find_new_support_resistance(df: pd.DataFrame, prominence: float = 0.02, width: int = 10) -> Dict[str, List[Level]]:
    """Identifies support and resistance levels from price data.

    This function uses peak finding on high and low prices to identify
    significant price levels. These levels are then clustered to group
    nearby values, and classified as support or resistance based on the
    last closing price. The historical high and low are also included.

    Args:
        df (pd.DataFrame): DataFrame with 'high', 'low', and 'close' columns.
        prominence (float, optional): The prominence of the peaks, as a
            fraction of the total price range. Defaults to 0.02.
        width (int, optional): The minimum width of the peaks. Defaults to 10.

    Returns:
        Dict[str, List[Level]]: A dictionary containing lists of the top 5
        support and resistance Level objects. Returns empty lists if the
        input data is insufficient.
    """
    if df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        return {'supports': [], 'resistances': []}

    price_range = df['high'].max() - df['low'].min()
    if price_range == 0:
        return {'supports': [], 'resistances': []}

    prominence_value = price_range * prominence

    resistance_indices, _ = find_peaks(df['high'], prominence=prominence_value, width=width)
    resistances = df['high'].iloc[resistance_indices].to_list()

    support_indices, _ = find_peaks(-df['low'], prominence=prominence_value, width=width)
    supports = df['low'].iloc[support_indices].to_list()

    all_levels = sorted(list(set(supports + resistances)))
    clustered_levels = []
    if all_levels:
        current_cluster = [all_levels[0]]
        for level in all_levels[1:]:
            if level <= np.mean(current_cluster) * 1.01:
                current_cluster.append(level)
            else:
                clustered_levels.append({'level': np.mean(current_cluster), 'strength': len(current_cluster)})
                current_cluster = [level]
        clustered_levels.append({'level': np.mean(current_cluster), 'strength': len(current_cluster)})

    final_supports = []
    final_resistances = []
    last_close = df['close'].iloc[-1]

    for data in clustered_levels:
        level = round(data['level'], 4)
        strength = data['strength']
        if level < last_close:
            final_supports.append({'value': level, 'strength': strength})
        else:
            final_resistances.append({'value': level, 'strength': strength})

    final_supports = sorted(final_supports, key=lambda x: x['value'], reverse=True)
    final_resistances = sorted(final_resistances, key=lambda x: x['value'])

    support_levels = []
    for i, sup in enumerate(final_supports):
        quality = "حرج" if i == 0 else ("قوي" if sup['strength'] >= 3 else "ثانوي")
        support_levels.append(Level(name=f"دعم عام ({quality})", value=sup['value'], level_type='support', quality=quality))

    resistance_levels = []
    for i, res in enumerate(final_resistances):
        quality = "حرج" if i == 0 else ("قوي" if res['strength'] >= 3 else "ثانوي")
        resistance_levels.append(Level(name=f"مقاومة عامة ({quality})", value=res['value'], level_type='resistance', quality=quality))

    # Add historical levels
    historical_low = df['low'].min()
    historical_high = df['high'].max()
    support_levels.append(Level(name="دعم تاريخي", value=historical_low, level_type='support', quality='تاريخي'))
    resistance_levels.append(Level(name="مقاومة تاريخية", value=historical_high, level_type='resistance', quality='تاريخي'))

    return {
        'supports': sorted(support_levels, key=lambda x: x.value, reverse=True)[:5],
        'resistances': sorted(resistance_levels, key=lambda x: x.value)[:5]
    }
