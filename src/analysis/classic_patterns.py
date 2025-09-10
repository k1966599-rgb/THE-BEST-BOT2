import pandas as pd
from typing import List
import logging
from .base_analysis import BaseAnalysis
from .patterns.pattern_utils import get_pivots
from .data_models import Pattern

# Import all pattern classes
from .patterns.ascending_triangle import AscendingTriangle
from .patterns.bull_flag import BullFlag
from .patterns.double_bottom import DoubleBottom
from .patterns.bear_flag import BearFlag
from .patterns.falling_wedge import FallingWedge
from .patterns.rising_wedge import RisingWedge

logger = logging.getLogger(__name__)

class ClassicPatterns(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        self.lookback_period = self.config.get('PATTERN_LOOKBACK', 90)
        self.price_tolerance = self.config.get('PATTERN_PRICE_TOLERANCE', 0.03)
        self.pattern_checkers = [
            AscendingTriangle, BullFlag, DoubleBottom,
            BearFlag, FallingWedge, RisingWedge,
        ]

    def analyze(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Orchestrates the detection of all classic patterns.
        Returns a list of standardized Pattern objects.
        """
        data_slice = df.tail(self.lookback_period)
        if len(data_slice) < 20:
            return []

        highs, lows = get_pivots(data_slice)
        if not highs or not lows:
            return []

        current_price = data_slice['close'].iloc[-1]
        all_found_patterns = []
        for checker_class in self.pattern_checkers:
            try:
                instance = checker_class(
                    data_slice, self.config, highs, lows,
                    current_price, self.price_tolerance, self.timeframe
                )
                found = instance.check()
                if found:
                    all_found_patterns.extend(found)
            except Exception as e:
                logger.warning(f"Error checking pattern {checker_class.__name__}: {e}")

        # In the future, we can sort these based on some criteria like confirmation status or breakout potential
        return all_found_patterns
