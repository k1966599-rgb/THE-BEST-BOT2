import numpy as np
import pandas as pd
from typing import Dict, List

from .pattern_utils import calculate_dynamic_confidence

def check_double_bottom(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                       current_price: float, price_tolerance: float) -> List[Dict]:
    """
    Detects Double Bottom patterns.
    """
    patterns = []
    if len(lows) < 2 or len(highs) < 1:
        return patterns

    for i in range(len(lows) - 1):
        for j in range(i + 1, len(lows)):
            bottom1 = lows[i]
            bottom2 = lows[j]

            # Check for price similarity
            if abs(bottom1['price'] - bottom2['price']) / bottom1['price'] > price_tolerance:
                continue

            # Find intervening high (neckline)
            intervening_highs = [h for h in highs if bottom1['index'] < h['index'] < bottom2['index']]
            if not intervening_highs:
                continue

            neckline = max(intervening_highs, key=lambda x: x['price'])
            neckline_price = neckline['price']

            # Bottoms must be below neckline
            if bottom1['price'] >= neckline_price or bottom2['price'] >= neckline_price:
                continue

            # Calculate target and stop loss
            height = neckline_price - np.mean([bottom1['price'], bottom2['price']])
            target = neckline_price + height
            stop_loss = min(bottom1['price'], bottom2['price']) * 0.99

            patterns.append({
                'name': 'قاع مزدوج (Double Bottom)',
                'status': 'قيد التكوين 🟡' if current_price < neckline_price else 'مكتمل ✅',
                'confidence': 70.0,
                'activation_level': neckline_price,
                'invalidation_level': min(bottom1['price'], bottom2['price']),
                'price_target': target,
                'stop_loss': stop_loss
            })
            if patterns: # Found the most recent one
                return patterns

    return patterns
