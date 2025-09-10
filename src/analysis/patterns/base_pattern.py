import pandas as pd
import numpy as np
from typing import Dict, List, Any
from abc import ABC, abstractmethod
from .pattern_utils import find_trend_line

class BasePattern(ABC):
    """
    An abstract base class for all pattern detection classes.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        self.df = df
        self.config = config
        self.highs = highs
        self.lows = lows
        self.current_price = current_price
        self.price_tolerance = price_tolerance
        self.found_patterns = []

    @abstractmethod
    def check(self) -> List[Dict]:
        """
        This method should be implemented by each pattern class.
        It should return a list of found patterns.
        """
        pass

    def _filter_pivots(self, search_window_bars: int) -> (List[Dict], List[Dict]):
        """
        Filters the pivot points to a specific search window.
        """
        search_window = min(search_window_bars, len(self.df) // 2)
        search_data = self.df.tail(search_window)
        window_highs = [h for h in self.highs if h['index'] >= search_data.index[0]]
        window_lows = [l for l in self.lows if l['index'] >= search_data.index[0]]
        return window_highs, window_lows

    def _calculate_trend_lines(self, window_highs: List[Dict], window_lows: List[Dict]) -> (Dict, Dict):
        """
        Calculates the trend lines for the given pivot points.
        """
        upper_trend = find_trend_line([p['index'] for p in window_highs], [p['price'] for p in window_highs])
        lower_trend = find_trend_line([p['index'] for p in window_lows], [p['price'] for p in window_lows])
        return upper_trend, lower_trend

    def _get_current_levels(self, upper_trend: Dict, lower_trend: Dict) -> (float, float):
        """
        Calculates the current resistance and support levels based on the trend lines.
        """
        current_index = len(self.df) - 1
        resistance_current = upper_trend['slope'] * current_index + upper_trend['intercept']
        support_current = lower_trend['slope'] * current_index + lower_trend['intercept']
        return resistance_current, support_current

    def _analyze_volume(self, window_highs: List[Dict], window_lows: List[Dict], start_index: int) -> Dict:
        """
        Analyzes the volume for the pattern.
        """
        volume_analysis = {}
        if 'volume' in self.df.columns:
            early_indices = [p['index'] for p in window_highs + window_lows if p['index'] <= start_index + 10]
            early_volume = np.mean([self.df.iloc[i]['volume'] for i in early_indices if i < len(self.df)]) if early_indices else 0

            current_index = len(self.df) - 1
            late_indices = [p['index'] for p in window_highs + window_lows if p['index'] >= current_index - 10]
            late_volume = np.mean([self.df.iloc[i]['volume'] for i in late_indices if i < len(self.df)]) if late_indices else 0

            avg_volume = self.df['volume'].mean()

            volume_analysis = {
                'early_volume_strength': early_volume / avg_volume if avg_volume > 0 else 1,
                'late_volume_strength': late_volume / avg_volume if avg_volume > 0 else 1,
                'volume_decline': early_volume > late_volume * 1.2 if early_volume > 0 and late_volume > 0 else False,
                'breakout_volume': self.df.iloc[-1]['volume'] / avg_volume if avg_volume > 0 else 1
            }
        return volume_analysis
