import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.linear_model import LinearRegression

from .pattern_utils import calculate_dynamic_confidence # Import from the central location

def check_ascending_triangle(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                           current_price: float, price_tolerance: float) -> List[Dict]:
    """
    Detects Ascending Triangle patterns.
    This function contains the core logic and will be called by the analysis module.
    """
    patterns = []
    if len(highs) < 2 or len(lows) < 2:
        return patterns

    # Find a flat resistance line
    resistance_candidates = []
    for i in range(len(highs) - 1):
        for j in range(i + 1, len(highs)):
            price_diff = abs(highs[j]['price'] - highs[i]['price']) / highs[i]['price']
            if price_diff <= price_tolerance:
                resistance_candidates.append((highs[i], highs[j]))

    if not resistance_candidates:
        return patterns

    # Find the best resistance line (most touches, most recent)
    best_resistance_price = 0
    max_touches = 0
    for r_pair in resistance_candidates:
        price = np.mean([p['price'] for p in r_pair])
        touches = len([h for h in highs if abs(h['price'] - price) / price <= price_tolerance])
        if touches > max_touches:
            max_touches = touches
            best_resistance_price = price

    if best_resistance_price == 0:
        return patterns

    resistance_line_price = best_resistance_price

    # Find higher lows below the resistance
    support_lows = [l for l in lows if l['price'] < resistance_line_price]
    if len(support_lows) < 2:
        return patterns

    # Fit a line to the lows
    x = np.array([l['index'] for l in support_lows]).reshape(-1, 1)
    y = np.array([l['price'] for l in support_lows])
    lr = LinearRegression().fit(x, y)

    # Check if the support line is ascending
    if lr.coef_[0] <= 0:
        return patterns

    # Check for convergence
    current_support_price = lr.predict(np.array([[len(df)-1]]))[0]
    if current_support_price > resistance_line_price:
        return patterns # Lines have crossed

    # Calculate target and stop loss
    height = resistance_line_price - lr.predict(np.array([[support_lows[0]['index']]]))[0]
    target = resistance_line_price + height
    stop_loss = support_lows[-1]['price'] * 0.99 # 1% below the last low

    patterns.append({
        'name': 'مثلث صاعد (Ascending Triangle)',
        'status': 'قيد التكوين 🟡' if current_price < resistance_line_price else 'مكتمل ✅',
        'confidence': 75.0, # Placeholder, can use dynamic confidence later
        'activation_level': resistance_line_price,
        'invalidation_level': stop_loss,
        'price_target': target,
        'stop_loss': stop_loss
    })

    return patterns
