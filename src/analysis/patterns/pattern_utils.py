import os
import importlib
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.signal import find_peaks
import warnings
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

def calculate_dynamic_confidence(df, config, base_confidence=70, is_bullish=True):
    """
    حساب الثقة الديناميكية للنماذج بناءً على قوة الإشارة والحجم والتقلبات
    """
    # ... (existing implementation) ...
    try:
        if 'volume' in df.columns:
            recent_volume = df['volume'].tail(10).mean()
            avg_volume = df['volume'].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        else:
            volume_ratio = 1
        if len(df) > 1:
            volatility = df['close'].pct_change().std()
        else:
            volatility = 0
        volume_adjustment = min(20, max(-20, (volume_ratio - 1) * 30))
        volatility_adjustment = min(15, max(-15, (0.02 - volatility) * 100))
        final_confidence = base_confidence + volume_adjustment + volatility_adjustment
        return max(30, min(95, final_confidence))
    except Exception as e:
        return base_confidence

# --- Moved from root __init__.py ---

class AdvancedPatternDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df.reset_index(drop=True, inplace=True)

    def _detect_pivot_points(self, order: int = 5) -> Tuple[List[Dict], List[Dict]]:
        high_peaks, _ = find_peaks(self.df['high'], distance=order, prominence=self.df['high'].std() * 0.5)
        low_peaks, _ = find_peaks(-self.df['low'], distance=order, prominence=self.df['low'].std() * 0.5)
        highs = [{'index': i, 'price': self.df.iloc[i]['high']} for i in high_peaks]
        lows = [{'index': i, 'price': self.df.iloc[i]['low']} for i in low_peaks]
        return highs, lows

    # Other helper methods from the old __init__.py can be pasted here if needed

def check_all_patterns(df: pd.DataFrame, config: dict = None,
                      highs: List[Dict] = None, lows: List[Dict] = None,
                      current_price: float = None, price_tolerance: float = None) -> List[Dict]:
    if config is None: config = {}
    if df is None or len(df) < 20: return []

    detector = AdvancedPatternDetector(df)
    if highs is None or lows is None:
        highs, lows = detector._detect_pivot_points()
    if current_price is None: current_price = df['close'].iloc[-1]
    if price_tolerance is None: price_tolerance = df['close'].std() * 0.05

    all_patterns = []

    # Static imports as fallback, dynamic loading is complex to get right
    from .ascending_triangle import check_ascending_triangle
    from .double_bottom import check_double_bottom
    from .bull_flag import check_bull_flag
    from .bear_flag import check_bear_flag
    from .falling_wedge import check_falling_wedge
    from .rising_wedge import check_rising_wedge

    pattern_checkers = [
        check_ascending_triangle, check_double_bottom, check_bull_flag,
        check_bear_flag, check_falling_wedge, check_rising_wedge
    ]

    for checker in pattern_checkers:
        try:
            found = checker(df, config, highs, lows, current_price, price_tolerance)
            if found:
                all_patterns.extend(found)
        except Exception as e:
            logger.error(f"Error in pattern checker {checker.__name__}: {e}")
            continue

    # Simplified sorting
    all_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    return all_patterns

def get_pivots(data: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
    """Helper function to get pivots, can be used by classic_patterns."""
    detector = AdvancedPatternDetector(data)
    return detector._detect_pivot_points()
