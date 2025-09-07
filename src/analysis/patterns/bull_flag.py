import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.linear_model import LinearRegression

def find_trend_line(x_values: List[int], y_values: List[float]) -> Dict:
    if len(x_values) < 2: return {'slope': 0, 'intercept': 0}
    x_array = np.array(x_values).reshape(-1, 1)
    y_array = np.array(y_values)
    reg = LinearRegression().fit(x_array, y_array)
    return {'slope': reg.coef_[0], 'intercept': reg.intercept_}

def check_bull_flag(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                   current_price: float, price_tolerance: float) -> List[Dict]:
    """
    Detects Bull Flag patterns.
    """
    patterns = []
    if len(highs) < 2 or len(lows) < 2:
        return patterns

    # Find flagpole
    for i in range(len(lows) - 1, -1, -1):
        flagpole_start = lows[i]
        potential_pole_highs = [h for h in highs if h['index'] > flagpole_start['index']]
        if not potential_pole_highs: continue

        flagpole_end = max(potential_pole_highs, key=lambda x: x['price'])
        flagpole_height = flagpole_end['price'] - flagpole_start['price']

        if flagpole_height <= 0: continue

        # Find flag
        flag_highs = [h for h in highs if h['index'] > flagpole_end['index']]
        flag_lows = [l for l in lows if l['index'] > flagpole_end['index']]

        if len(flag_highs) < 2 or len(flag_lows) < 2: continue

        # Check for retracement
        deepest_low = min(flag_lows, key=lambda x: x['price'])['price']
        if (flagpole_end['price'] - deepest_low) / flagpole_height > 0.5: # Retracement > 50%
            continue

        # Check for parallel-ish channel
        upper_line = find_trend_line([p['index'] for p in flag_highs], [p['price'] for p in flag_highs])
        lower_line = find_trend_line([p['index'] for p in flag_lows], [p['price'] for p in flag_lows])

        # Slopes should be negative (downtrending flag)
        if upper_line['slope'] > 0 or lower_line['slope'] > 0:
            continue

        resistance_current = upper_line['slope'] * (len(df) - 1) + upper_line['intercept']

        patterns.append({
            'name': 'علم صاعد (Bull Flag)',
            'status': 'قيد التكوين 🟡' if current_price < resistance_current else 'مكتمل ✅',
            'confidence': 70.0,
            'activation_level': resistance_current,
            'invalidation_level': min([l['price'] for l in flag_lows]),
            'price_target': resistance_current + flagpole_height,
            'stop_loss': min([l['price'] for l in flag_lows]) * 0.99
        })
        # Found the most recent one, break
        if patterns:
            break

    return patterns
