import pandas as pd
from typing import List, Dict
import logging
from .base_analysis import BaseAnalysis
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
    """Analyzes and detects classic technical analysis patterns.

    This class orchestrates the detection of various classic patterns like
    Ascending Triangle, Bull Flag, Double Bottom, etc. It uses a set of
    pattern checker classes to identify these patterns in the given market
    data.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        """Initializes the ClassicPatterns analysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed. Defaults to '1h'.
        """
        super().__init__(config, timeframe)
        self.lookback_period = self.config.get('PATTERN_LOOKBACK', 90)
        self.price_tolerance = self.config.get('PATTERN_PRICE_TOLERANCE', 0.03)
        self.pattern_checkers = [
            AscendingTriangle, BullFlag, DoubleBottom,
            BearFlag, FallingWedge, RisingWedge,
        ]

    def analyze(self, df: pd.DataFrame, highs: List[Dict], lows: List[Dict], trend_context: dict = None) -> List[Pattern]:
        """Orchestrates the detection of all classic patterns using pre-calculated pivots.

        This method slices the data and then iterates through a list of pattern
        checker classes to identify any matching patterns.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.
            highs (List[Dict]): A list of pivot high points.
            lows (List[Dict]): A list of pivot low points.
            trend_context (dict, optional): A dictionary containing trend
                analysis context. Defaults to None.

        Returns:
            List[Pattern]: A list of standardized Pattern objects for all
            found patterns. Returns an empty list if no patterns are found
            or if the data is insufficient.
        """
        data_slice = df.tail(self.lookback_period)
        if len(data_slice) < 20:
            return []

        if not highs or not lows:
            return []

        current_price = data_slice['close'].iloc[-1]
        all_found_patterns = []
        for checker_class in self.pattern_checkers:
            try:
                instance = checker_class(
                    data_slice, self.config, highs, lows,
                    current_price, self.price_tolerance, self.timeframe,
                    trend_context=trend_context
                )
                found = instance.check()
                if found:
                    all_found_patterns.extend(found)
            except Exception as e:
                logger.warning(f"Error checking pattern {checker_class.__name__}: {e}")

        # In the future, we can sort these based on some criteria like confirmation status or breakout potential
        return all_found_patterns
