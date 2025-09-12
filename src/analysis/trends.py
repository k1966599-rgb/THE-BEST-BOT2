import pandas as pd
from typing import Dict, Any
import logging
from .base_analysis import BaseAnalysis

logger = logging.getLogger(__name__)

class TrendAnalysis(BaseAnalysis):
    """Analyzes market trend using EMAs and ADX.

    This class determines the trend direction (uptrend, downtrend, sideways)
    based on the alignment of short, medium, and long-term Exponential Moving
    Averages (EMAs). It uses the Average Directional Index (ADX) to gauge
    the strength of the trend.
    """
    def __init__(self, config: dict = None, timeframe: str = None):
        """Initializes the TrendAnalysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings for trend analysis periods. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed. Defaults to None.
        """
        super().__init__(config, timeframe)
        self.short_period = self.config.get('TREND_SHORT_PERIOD', 20)
        self.medium_period = self.config.get('TREND_MEDIUM_PERIOD', 50)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)
        self.adx_period = self.config.get('ADX_PERIOD', 14)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Determines trend direction and strength.

        It assigns a score based on EMA alignment and then adjusts this
        score based on the ADX value to reflect trend strength.

        Args:
            df (pd.DataFrame): The DataFrame containing market data and
                pre-calculated indicator values. The column names for the
                indicators can be in upper or lower case.

        Returns:
            Dict[str, Any]: A dictionary containing the 'total_score',
            'trend_direction', 'is_trending' status, and 'adx_value'.
            Returns a score of 0 with an error if data is insufficient.
        """
        try:
            # Column names from pandas_ta can be upper or lower case
            ema_short_col = f'EMA_{self.short_period}'
            ema_medium_col = f'EMA_{self.medium_period}'
            ema_long_col = f'EMA_{self.long_period}'
            adx_col = f'ADX_{self.adx_period}'

            required_len = self.long_period
            if len(df) < required_len:
                return {'error': f'Not enough data. Need {required_len} rows.', 'total_score': 0}

            latest = df.iloc[-1]

            # Function to get value regardless of case
            def get_val(col_name):
                return latest.get(col_name.upper(), latest.get(col_name.lower()))

            current_price = get_val('close')
            ema_short = get_val(ema_short_col)
            ema_medium = get_val(ema_medium_col)
            ema_long = get_val(ema_long_col)
            adx = get_val(adx_col)

            if any(v is None for v in [current_price, ema_short, ema_medium, ema_long, adx]):
                 return {'error': f'One of the required indicator values is missing or None. Required: close, {ema_short_col}, {ema_medium_col}, {ema_long_col}, {adx_col}', 'total_score': 0}

            score = 0
            if current_price > ema_short > ema_medium > ema_long: score = 3
            elif current_price > ema_short > ema_medium: score = 2
            elif current_price < ema_short < ema_medium < ema_long: score = -3
            elif current_price < ema_short < ema_medium: score = -2

            total_score = score * 1.5 if adx > 25 else score * 0.5 if adx < 20 else score
            direction = 'Uptrend' if score > 0 else 'Downtrend' if score < 0 else 'Sideways'

            return {
                'total_score': round(total_score, 2),
                'trend_direction': direction,
                'is_trending': bool(adx > 25),
                'adx_value': round(adx, 2)
            }
        except Exception as e:
            logger.exception("Error in TrendAnalysis")
            return {'error': str(e), 'total_score': 0}
