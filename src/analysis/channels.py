import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base_analysis import BaseAnalysis
from .data_models import Level
import logging
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

class PriceChannels(BaseAnalysis):
    """Analyzes price channels using linear regression.

    This class calculates price channels by fitting a linear regression model
    to the closing prices. The upper and lower bands of the channel are
    determined by adding or subtracting a multiple of the standard deviation
    of the residuals. The results are returned as standardized Level objects.
    """

    def __init__(self, config: dict = None, timeframe: str = '1h'):
        """Initializes the PriceChannels analysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed. Defaults to '1h'.
        """
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('CHANNEL_LOOKBACK', self.config.get('CHANNEL_LOOKBACK', 90))
        self.std_dev_multiplier = overrides.get('CHANNEL_STD_DEV_MULTIPLIER', self.config.get('CHANNEL_STD_DEV_MULTIPLIER', 1.5))

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """Calculates price channel boundaries.

        This method uses a linear regression trendline and standard deviation
        to identify the upper (resistance) and lower (support) boundaries of
        the price channel.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.

        Returns:
            Dict[str, List[Level]]: A dictionary containing lists of support
            and resistance Level objects. Returns empty lists if the DataFrame
            is too small or if an error occurs.
        """
        if len(df) < self.lookback:
            return {'supports': [], 'resistances': []}

        try:
            data = df.tail(self.lookback).copy()
            x = np.arange(len(data)).reshape(-1, 1)
            y = data['close'].values

            model = LinearRegression()
            model.fit(x, y)

            trendline = model.predict(x)
            residuals = y - trendline
            std_dev = residuals.std()

            upper_band = trendline + (self.std_dev_multiplier * std_dev)
            lower_band = trendline - (self.std_dev_multiplier * std_dev)

            latest_upper_band = round(upper_band[-1], 4)
            latest_lower_band = round(lower_band[-1], 4)

            supports = [
                Level(
                    name="دعم قناة سعرية",
                    value=latest_lower_band,
                    level_type='support',
                    quality='قاع'
                )
            ]
            resistances = [
                Level(
                    name="مقاومة قناة سعرية",
                    value=latest_upper_band,
                    level_type='resistance',
                    quality='قمة'
                )
            ]

            return {'supports': supports, 'resistances': resistances}

        except Exception as e:
            logger.exception(f"Error during channel analysis for timeframe {self.timeframe}")
            return {'supports': [], 'resistances': []}
