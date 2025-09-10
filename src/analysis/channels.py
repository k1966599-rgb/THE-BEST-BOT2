import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base_analysis import BaseAnalysis
from .data_models import Level
import logging
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

class PriceChannels(BaseAnalysis):
    """
    Analyzes price channels and returns standardized Level objects.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('CHANNEL_LOOKBACK', self.config.get('CHANNEL_LOOKBACK', 90))
        self.std_dev_multiplier = overrides.get('CHANNEL_STD_DEV_MULTIPLIER', self.config.get('CHANNEL_STD_DEV_MULTIPLIER', 1.5))

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """
        Calculates price channel boundaries and returns them as Level objects.
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
