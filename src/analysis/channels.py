import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_analysis import BaseAnalysis
import logging
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

class PriceChannels(BaseAnalysis):
    """
    Analyzes price channels using linear regression.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        # Use timeframe-specific overrides if they exist in the config
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('CHANNEL_LOOKBACK', self.config.get('CHANNEL_LOOKBACK', 90))
        self.std_dev_multiplier = overrides.get('CHANNEL_STD_DEV_MULTIPLIER', self.config.get('CHANNEL_STD_DEV_MULTIPLIER', 1.5))

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates the price channel based on a linear regression trendline.

        :param df: DataFrame with historical price data.
        :return: A dictionary containing channel information.
        """
        if len(df) < self.lookback:
            return {'error': f'Not enough data for channel analysis. Need {self.lookback} periods.', 'channel_score': 0}

        try:
            data = df.tail(self.lookback).copy()

            # Prepare data for regression
            x = np.arange(len(data)).reshape(-1, 1)
            y = data['close'].values

            # Fit linear regression model
            model = LinearRegression()
            model.fit(x, y)

            # Calculate trendline
            trendline = model.predict(x)
            data['trendline'] = trendline

            # Calculate residuals (distance from trendline)
            residuals = y - trendline

            # Calculate standard deviation of residuals
            std_dev = residuals.std()

            # Calculate channel boundaries
            data['upper_channel'] = trendline + (self.std_dev_multiplier * std_dev)
            data['lower_channel'] = trendline - (self.std_dev_multiplier * std_dev)

            # Get the latest values
            latest = data.iloc[-1]
            current_price = latest['close']
            upper_band = latest['upper_channel']
            lower_band = latest['lower_channel']
            center_line = latest['trendline']

            # Determine position within the channel
            channel_width = upper_band - lower_band
            position_pct = (current_price - lower_band) / channel_width if channel_width > 0 else 0.5

            # Determine slope (trend direction)
            slope = model.coef_[0]
            slope_strength = abs(slope) / (data['close'].mean() * 0.0001) # Normalized strength

            channel_trend = "صاعد" if slope > 0 else "هابط" if slope < 0 else "عرضي"

            # Scoring logic
            channel_score = 0
            if channel_trend == "صاعد":
                channel_score += 5
                if position_pct < 0.25: # Nearing lower band in uptrend is a buy signal
                    channel_score += 5
            elif channel_trend == "هابط":
                channel_score -= 5
                if position_pct > 0.75: # Nearing upper band in downtrend is a sell signal
                    channel_score += -5

            channel_score *= (1 + min(slope_strength / 5, 1)) # Weight by slope strength

            return {
                'upper_band': round(upper_band, 4),
                'lower_band': round(lower_band, 4),
                'center_line': round(center_line, 4),
                'slope': round(slope, 4),
                'slope_strength': round(slope_strength, 2),
                'channel_trend': channel_trend,
                'position_in_channel': round(position_pct * 100, 2),
                'channel_score': round(channel_score, 2)
            }

        except Exception as e:
            logger.exception(f"Error during channel analysis for timeframe {self.timeframe}")
            return {'error': str(e), 'channel_score': 0}
