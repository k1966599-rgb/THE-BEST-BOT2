import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_line_equation_from_points(points: np.ndarray) -> Optional[Dict[str, float]]:
    """Calculates the slope and intercept of a line given a set of points."""
    if len(points) < 2:
        return None
    x = points[:, 0]
    y = points[:, 1]
    slope, intercept = np.polyfit(x, y, 1)
    return {'slope': slope, 'intercept': intercept}

class PriceChannels:
    """
    وحدة تحليل القنوات السعرية المتقدمة
    Uses a more robust pivot-based method instead of simple linear regression.
    """
    def __init__(self, df: pd.DataFrame, config: dict = None, timeframe: str = '1h'):
        self.df = df.copy()
        if config is None: config = {}
        self.config = config
        self.timeframe = timeframe

        overrides = config.get('TIMEFRAME_OVERRIDES', {}).get(timeframe, {})
        self.lookback = overrides.get('CHANNEL_LOOKBACK', config.get('CHANNEL_LOOKBACK', 50))

    def get_comprehensive_channel_analysis(self) -> Dict:
        """
        Returns a summary of the most prominent channel found.
        """
        try:
            logger.info(f"Starting Channel analysis with lookback {self.lookback}.")
            if len(self.df) < self.lookback:
                logger.warning(f"Not enough data for Channel analysis. Data has {len(self.df)} rows, need {self.lookback}.")
                return {'error': f'Not enough data for Channel analysis.', 'total_score': 0}

        data = self.df.tail(self.lookback)

            prominence = data['close'].std() * 0.5
            high_pivots_idx, _ = find_peaks(data['high'], prominence=prominence, distance=3)
            low_pivots_idx, _ = find_peaks(-data['low'], prominence=prominence, distance=3)
            logger.info(f"Found {len(high_pivots_idx)} high pivots and {len(low_pivots_idx)} low pivots for channel.")

            if len(high_pivots_idx) < 2 or len(low_pivots_idx) < 2:
                 logger.warning("Not enough pivots to form a channel.")
                 return {'error': 'Not enough pivots to form a channel.', 'total_score': 0}

            high_points = np.array([[i, data['high'].iloc[i]] for i in high_pivots_idx])
            low_points = np.array([[i, data['low'].iloc[i]] for i in low_pivots_idx])

            upper_line = get_line_equation_from_points(high_points)
            lower_line = get_line_equation_from_points(low_points)

            if not upper_line or not lower_line:
                logger.warning("Could not calculate channel lines from pivots.")
                return {'error': 'Could not calculate channel lines.', 'total_score': 0}

            avg_slope = (upper_line['slope'] + lower_line['slope']) / 2
            center_intercept = (upper_line['intercept'] + lower_line['intercept']) / 2

            high_center = upper_line['slope'] * (len(data)/2) + upper_line['intercept']
            low_center = lower_line['slope'] * (len(data)/2) + lower_line['intercept']
            channel_width = high_center - low_center

            upper_intercept = center_intercept + (channel_width / 2)
            lower_intercept = center_intercept - (channel_width / 2)

            last_x = len(data) - 1
            current_upper = avg_slope * last_x + upper_intercept
            current_lower = avg_slope * last_x + lower_intercept

            if avg_slope > 0.05: channel_type = "قناة صاعدة"
            elif avg_slope < -0.05: channel_type = "قناة هابطة"
            else: channel_type = "قناة عرضية"

            score = 0
            current_price = data['close'].iloc[-1]
            if current_price < current_lower: score = 1
            if current_price > current_upper: score = -1

            logger.info(f"Channel analysis complete. Type: {channel_type}, Score: {score}.")
            return {
                'channel_info': f"{channel_type}: ${current_lower:,.2f} - ${current_upper:,.2f}",
                'total_score': score,
                'details': { "type": channel_type, "upper_bound": current_upper, "lower_bound": current_lower }
            }
        except Exception as e:
            logger.exception("An unexpected error occurred during Channel analysis.")
            return {'error': str(e), 'total_score': 0}
