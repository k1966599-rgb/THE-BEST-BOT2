import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Any
from .data_models import Level
from .base_analysis import BaseAnalysis

class NewSupportResistanceAnalysis(BaseAnalysis):
    """
    Adapter class to integrate the S/R function into the analysis orchestrator.
    This class now receives pre-calculated pivots and passes them to the analysis function.
    """
    def analyze(self, df: pd.DataFrame, highs: List[Dict], lows: List[Dict]) -> Dict[str, Any]:
        """
        Runs the support and resistance analysis using pre-calculated pivots.
        """
        return _find_new_support_resistance(df, highs, lows)

def _find_new_support_resistance(df: pd.DataFrame, highs: List[Dict], lows: List[Dict]) -> Dict[str, List[Level]]:
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

    # Use the prices from the pre-calculated pivots
    resistances = [h['price'] for h in highs]
    supports = [l['price'] for l in lows]

    all_levels = sorted(list(set(supports + resistances)))

    # New clustering logic with volume calculation
    clustered_levels = []
    if all_levels:
        clusters = []
        current_cluster = [all_levels[0]]
        for level in all_levels[1:]:
            if level <= np.mean(current_cluster) * 1.01:
                current_cluster.append(level)
            else:
                clusters.append(current_cluster)
                current_cluster = [level]
        clusters.append(current_cluster)

        for cluster in clusters:
            level_mean = np.mean(cluster)
            level_min = min(cluster)
            level_max = max(cluster)

            # Calculate volume for the zone
            zone_df = df[(df['low'] <= level_max) & (df['high'] >= level_min)]
            total_volume = zone_df['volume'].sum()

            clustered_levels.append({
                'level': level_mean,
                'strength': total_volume, # Using raw volume for now, will normalize later
                'min_val': level_min,
                'max_val': level_max
            })

    # Normalize strength (volume) to a 0-100 scale for easier comparison
    if clustered_levels:
        max_strength = max(c['strength'] for c in clustered_levels)
        if max_strength > 0:
            for c in clustered_levels:
                c['strength'] = (c['strength'] / max_strength) * 100

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
        quality = "حرج" if i == 0 else ("قوي" if sup['strength'] >= 70 else "ثانوي")
        template_key = 'previous_support_critical' if quality == "حرج" else 'previous_support_secondary'
        zone_data = {'min_val': sup['min_val'], 'max_val': sup['max_val'], 'volume_strength': sup['strength']}
        support_levels.append(Level(
            name=f"دعم عام سابق ({quality})",
            value=sup['value'],
            level_type='support',
            quality=quality,
            template_key=template_key,
            raw_data=zone_data
        ))

    resistance_levels = []
    for i, res in enumerate(final_resistances):
        quality = "حرج" if i == 0 else ("قوي" if res['strength'] >= 70 else "ثانوي")
        name = f"مقاومة رئيسية ({quality})" if i == 0 else f"مقاومة عامة ({quality})"
        template_key = 'main_resistance' if i == 0 else 'secondary_resistance'
        zone_data = {'min_val': res['min_val'], 'max_val': res['max_val'], 'volume_strength': res['strength']}
        resistance_levels.append(Level(
            name=name,
            value=res['value'],
            level_type='resistance',
            quality=quality,
            template_key=template_key,
            raw_data=zone_data
        ))

    # Add historical levels
    historical_low = df['low'].min()
    historical_high = df['high'].max()
    support_levels.append(Level(name="قاع تاريخي", value=historical_low, level_type='support', quality='تاريخي', template_key='historical_bottom'))
    resistance_levels.append(Level(name="قمة تاريخية", value=historical_high, level_type='resistance', quality='تاريخي', template_key='historical_top'))

    return {
        'supports': sorted(support_levels, key=lambda x: x.value, reverse=True)[:5],
        'resistances': sorted(resistance_levels, key=lambda x: x.value)[:5]
    }
