import pandas as pd
from typing import Dict, Any
import logging
from .base_analysis import BaseAnalysis

logger = logging.getLogger(__name__)

class TrendAnalysis(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = None):
        super().__init__(config, timeframe)
        self.short_period = self.config.get('TREND_SHORT_PERIOD', 20)
        self.medium_period = self.config.get('TREND_MEDIUM_PERIOD', 50)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)
        self.adx_period = self.config.get('ADX_PERIOD', 14)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        try:
            required_len = self.long_period
            if len(df) < required_len:
                return {'error': f'Not enough data. Need {required_len} rows.', 'total_score': 0}

            latest = df.iloc[-1]
            required_cols = [
                'close', f'EMA_{self.short_period}', f'EMA_{self.medium_period}',
                f'EMA_{self.long_period}', f'ADX_{self.adx_period}'
            ]
            if not all(col in latest.index for col in required_cols):
                return {'error': f'Missing one or more required columns: {required_cols}', 'total_score': 0}

            current_price = latest['close']
            ema_short = latest[f'EMA_{self.short_period}']
            ema_medium = latest[f'EMA_{self.medium_period}']
            ema_long = latest[f'EMA_{self.long_period}']
            adx = latest[f'ADX_{self.adx_period}']

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
