import pandas as pd
from typing import Dict, Any
import logging

from .base_analysis import BaseAnalysis

logger = logging.getLogger(__name__)

class TrendAnalysis(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = None):
        super().__init__(config, timeframe)
        # Using more descriptive names for periods based on their default values
        self.short_period = self.config.get('TREND_SHORT_PERIOD', 20)
        self.medium_period = self.config.get('TREND_MEDIUM_PERIOD', 50)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)
        self.adx_period = self.config.get('ADX_PERIOD', 14)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Performs trend analysis using pre-calculated EMAs and ADX from the dataframe.
        This focuses on trend direction and strength based on indicators.
        """
        try:
            logger.info("Starting Trend analysis.")
            required_len = self.long_period
            if len(df) < required_len:
                logger.warning(f"Not enough data for Trend analysis. Data has {len(df)} rows, need {required_len}.")
                return {'error': f'Not enough data for Trend analysis. Need {required_len} periods.', 'total_score': 0}

            latest = df.iloc[-1]

            # Ensure required columns exist
            required_cols = [
                'Close',
                f'EMA_{self.short_period}',
                f'EMA_{self.medium_period}',
                f'EMA_{self.long_period}',
                f'ADX_{self.adx_period}'
            ]
            if not all(col in latest.index for col in required_cols):
                logger.error(f"One or more required indicator columns are missing for trend analysis. Required: {required_cols}")
                return {'error': 'One or more required indicator columns are missing for trend analysis.', 'total_score': 0}

            current_price = latest['Close']
            ema_short = latest[f'EMA_{self.short_period}']
            ema_medium = latest[f'EMA_{self.medium_period}']
            ema_long = latest[f'EMA_{self.long_period}']
            adx = latest[f'ADX_{self.adx_period}']

            trend_direction_score = 0
            # More robust conditions
            if current_price > ema_short and ema_short > ema_medium: trend_direction_score = 2
            elif ema_short > ema_medium and ema_medium > ema_long: trend_direction_score = 3
            elif current_price < ema_short and ema_short < ema_medium: trend_direction_score = -2
            elif ema_short < ema_medium and ema_medium < ema_long: trend_direction_score = -3

            # Calculate final score based on trend strength (ADX)
            if adx > 25:
                total_score = trend_direction_score * 1.5
            elif adx < 20:
                total_score = trend_direction_score * 0.5
            else:
                total_score = trend_direction_score

            trend_direction = 'Uptrend' if trend_direction_score > 0 else 'Downtrend' if trend_direction_score < 0 else 'Sideways'
            logger.info(f"Trend analysis complete. Direction: {trend_direction}, ADX: {adx:.2f}, Score: {total_score:.2f}.")

            return {
                'total_score': round(total_score, 2),
                'trend_direction': trend_direction,
                'is_trending': bool(adx > 25),
                'adx_value': round(adx, 2)
            }
        except Exception as e:
            logger.exception("An unexpected error occurred during Trend analysis.")
            return {'error': str(e), 'total_score': 0}
