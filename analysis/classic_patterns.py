import pandas as pd
from typing import Dict
import logging

# Import the refactored, modular components
from .patterns.utils import get_pivots
from .patterns import check_all_patterns

logger = logging.getLogger(__name__)

class ClassicPatterns:
    """
    This class serves as a wrapper for the modular pattern analysis system.
    It orchestrates fetching pivots and running all configured pattern checks.
    """
    def __init__(self, df: pd.DataFrame, config: dict = None, timeframe: str = '1h'):
        self.df = df
        if config is None: config = {}
        self.config = config
        self.timeframe = timeframe

        # --- Configuration ---
        overrides = config.get('TIMEFRAME_OVERRIDES', {}).get(timeframe, {})
        self.lookback_period = overrides.get('PATTERN_LOOKBACK', config.get('PATTERN_LOOKBACK', 90))
        self.price_tolerance = overrides.get('PATTERN_PRICE_TOLERANCE', config.get('PATTERN_PRICE_TOLERANCE', 0.03))

        # --- Data Slice ---
        self.data = self.df.tail(self.lookback_period)
        self.current_price = self.data['close'].iloc[-1] if not self.data.empty else 0

    def get_comprehensive_patterns_analysis(self) -> Dict:
        """
        Orchestrates the pattern detection process using the new modular structure.
        """
        try:
            logger.info(f"Starting pattern analysis with lookback {self.lookback_period} (data size: {len(self.data)} rows).")
            if len(self.data) < 20:
                logger.warning("Not enough data for pattern analysis.")
                return {'error': 'Not enough data for pattern analysis.', 'pattern_score': 0, 'found_patterns': []}

        # 1. Get pivot points using the utility function
            highs, lows = get_pivots(self.data)
            if not highs or not lows:
                logger.warning("Could not determine pivots from the data.")
                return {'error': 'Could not determine pivots.', 'pattern_score': 0, 'found_patterns': []}
            logger.info(f"Found {len(highs)} pivot highs and {len(lows)} pivot lows.")

            # 2. Run all pattern checks from the new 'patterns' package
            all_found_patterns = check_all_patterns(
                df=self.df,
                config=self.config,
                highs=highs,
                lows=lows,
                current_price=self.current_price,
                price_tolerance=self.price_tolerance
            )
            logger.info(f"check_all_patterns found {len(all_found_patterns)} potential patterns.")

            # 3. Calculate score based on the results
            pattern_score = 0
            if all_found_patterns:
                for p in all_found_patterns:
                    # Bullish patterns add to the score, bearish ones subtract
                    score_multiplier = 1 if 'قاع' in p['name'] or 'صاعد' in p['name'] else -1

                    if p.get('status') == "مكتمل ✅":
                        pattern_score += 2 * score_multiplier
                    else: # 'قيد التكوين 🟡'
                        pattern_score += 1 * score_multiplier

                # Sort patterns by confidence for better presentation
                all_found_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)

            logger.info(f"Pattern analysis complete. Final score: {pattern_score}, Patterns returned: {len(all_found_patterns)}.")
            return {
                'found_patterns': all_found_patterns,
                'pattern_score': pattern_score,
                'error': None
            }
        except Exception as e:
            logger.exception("An unexpected error occurred during pattern analysis.")
            return {'error': str(e), 'pattern_score': 0, 'found_patterns': []}

    def get_comprehensive_pattern_analysis(self) -> Dict: # For backward compatibility
        return self.get_comprehensive_patterns_analysis()
