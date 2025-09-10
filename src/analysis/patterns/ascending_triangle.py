import numpy as np
import pandas as pd
from typing import List, Dict
from sklearn.linear_model import LinearRegression

from .base_pattern import BasePattern
from ..data_models import Pattern

class AscendingTriangle(BasePattern):
    """
    A class for detecting the Ascending Triangle pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Ascending Triangle"
        self.timeframe = timeframe

    def check(self) -> List[Pattern]:
        """
        Checks for the Ascending Triangle pattern and returns Pattern objects.
        """
        if len(self.highs) < 2 or len(self.lows) < 2:
            return []

        # Find horizontal resistance line
        resistance_candidates = []
        for i in range(len(self.highs) - 1):
            for j in range(i + 1, len(self.highs)):
                if abs(self.highs[j]['price'] - self.highs[i]['price']) / self.highs[i]['price'] <= self.price_tolerance:
                    resistance_candidates.append((self.highs[i], self.highs[j]))

        if not resistance_candidates: return []

        best_res_price = max([np.mean([p['price'] for p in r_pair]) for r_pair in resistance_candidates])

        # Find rising support line
        support_lows = [l for l in self.lows if l['price'] < best_res_price]
        if len(support_lows) < 2: return []

        x = np.array([l['index'] for l in support_lows]).reshape(-1, 1)
        y = np.array([l['price'] for l in support_lows])
        lr = LinearRegression().fit(x, y)

        if lr.coef_[0] <= 0: return []  # Slope must be positive

        # Calculate targets and levels
        height = best_res_price - lr.predict(np.array([[support_lows[0]['index']]]))[0]
        if height <= 0: return []

        target1 = best_res_price + height
        target2 = best_res_price + height * 1.618
        target3 = best_res_price + height * 2.618
        stop_loss = support_lows[-1]['price'] * 0.99
        status = 'قيد التكوين' if self.current_price < best_res_price else 'مفعل'

        pattern = Pattern(
            name='مثلث صاعد',
            status=status,
            timeframe=self.timeframe,
            activation_level=round(best_res_price, 4),
            invalidation_level=round(stop_loss, 4),
            target1=round(target1, 4),
            target2=round(target2, 4),
            target3=round(target3, 4)
        )
        return [pattern]
