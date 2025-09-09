import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.linear_model import LinearRegression

from .base_pattern import BasePattern

class AscendingTriangle(BasePattern):
    """
    A class for detecting the Ascending Triangle pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Ascending Triangle"

    def check(self) -> List[Dict]:
        """
        Checks for the Ascending Triangle pattern.
        """
        if len(self.highs) < 2 or len(self.lows) < 2:
            return []

        resistance_candidates = []
        for i in range(len(self.highs) - 1):
            for j in range(i + 1, len(self.highs)):
                price_diff = abs(self.highs[j]['price'] - self.highs[i]['price']) / self.highs[i]['price']
                if price_diff <= self.price_tolerance:
                    resistance_candidates.append((self.highs[i], self.highs[j]))

        if not resistance_candidates:
            return []

        best_resistance_price = 0
        max_touches = 0
        for r_pair in resistance_candidates:
            price = np.mean([p['price'] for p in r_pair])
            touches = len([h for h in self.highs if abs(h['price'] - price) / price <= self.price_tolerance])
            if touches > max_touches:
                max_touches = touches
                best_resistance_price = price

        if best_resistance_price == 0:
            return []

        resistance_line_price = best_resistance_price

        support_lows = [l for l in self.lows if l['price'] < resistance_line_price]
        if len(support_lows) < 2:
            return []

        x = np.array([l['index'] for l in support_lows]).reshape(-1, 1)
        y = np.array([l['price'] for l in support_lows])
        lr = LinearRegression().fit(x, y)

        if lr.coef_[0] <= 0:
            return []

        current_support_price = lr.predict(np.array([[len(self.df)-1]]))[0]
        if current_support_price > resistance_line_price:
            return []

        height = resistance_line_price - lr.predict(np.array([[support_lows[0]['index']]]))[0]
        target = resistance_line_price + height
        stop_loss = support_lows[-1]['price'] * 0.99

        self.found_patterns.append({
            'name': 'مثلث صاعد (Ascending Triangle)',
            'status': 'قيد التكوين 🟡' if self.current_price < resistance_line_price else 'مكتمل ✅',
            'confidence': 75.0,
            'activation_level': resistance_line_price,
            'invalidation_level': stop_loss,
            'price_target': target,
            'stop_loss': stop_loss
        })

        return self.found_patterns
