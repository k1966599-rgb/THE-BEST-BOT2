import pandas as pd
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from .patterns.pattern_utils import get_pivots, calculate_dynamic_confidence

# Import all the individual pattern checker functions
from .patterns.ascending_triangle import AscendingTriangle
from .patterns.bull_flag import check_bull_flag
from .patterns.double_bottom import check_double_bottom
from .patterns.bear_flag import BearFlag
from .patterns.falling_wedge import FallingWedge
from .patterns.rising_wedge import RisingWedge

class ClassicPatterns(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        self.lookback_period = self.config.get('PATTERN_LOOKBACK', 90)
        self.price_tolerance = self.config.get('PATTERN_PRICE_TOLERANCE', 0.03)
        self.pattern_checkers = [
            AscendingTriangle,
            check_bull_flag,
            check_double_bottom,
            BearFlag,
            FallingWedge,
            RisingWedge,
        ]

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        data_slice = df.tail(self.lookback_period)
        if len(data_slice) < 20:
            return {'error': 'Not enough data for pattern analysis.', 'pattern_score': 0}

        highs, lows = get_pivots(data_slice)
        if not highs or not lows:
            return {'error': 'Could not determine pivots.', 'pattern_score': 0}

        current_price = data_slice['close'].iloc[-1]

        all_found_patterns = []
        for checker in self.pattern_checkers:
            try:
                # if the checker is a class, instantiate it
                if isinstance(checker, type):
                    instance = checker(data_slice, self.config, highs, lows, current_price, self.price_tolerance)
                    found = instance.check()
                else: # it's a function
                    found = checker(data_slice, self.config, highs, lows, current_price, self.price_tolerance)

                if found:
                    all_found_patterns.extend(found)
            except Exception as e:
                # Log this error
                pass

        # Enhance patterns with dynamic confidence and sort
        for p in all_found_patterns:
            p['confidence'] = calculate_dynamic_confidence(data_slice, base_confidence=p.get('confidence', 65))

        all_found_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        pattern_score = 0
        if all_found_patterns:
            primary_pattern = all_found_patterns[0]
            if 'صاعد' in primary_pattern['name'] or 'قاع' in primary_pattern['name']:
                pattern_score = primary_pattern['confidence'] / 20 # Scale to a reasonable score
            else:
                pattern_score = -primary_pattern['confidence'] / 20

        return {
            'found_patterns': all_found_patterns,
            'pattern_score': pattern_score
        }
