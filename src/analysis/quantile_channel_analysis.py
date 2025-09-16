import pandas as pd
import numpy as np
from typing import Dict, List
from sklearn.linear_model import QuantileRegressor
from .base_analysis import BaseAnalysis
from .data_models import Level
import logging

logger = logging.getLogger(__name__)

class QuantileChannelAnalysis(BaseAnalysis):
    """
    Analyzes price channels using Quantile Regression. This method is more robust
    to outliers and non-linear trends than simple linear regression.
    """
    def __init__(self, config: dict, timeframe: str):
        super().__init__(config, timeframe)
        self.lookback_period = self.params.get('channel_lookback', 90)
        self.upper_quantile = self.params.get('channel_upper_quantile', 0.95)
        self.lower_quantile = self.params.get('channel_lower_quantile', 0.05)

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """
        Calculates the upper and lower boundaries of the price channel using
        quantile regression.
        """
        if len(df) < self.lookback_period:
            return {'supports': [], 'resistances': []}

        try:
            data = df.tail(self.lookback_period).copy()
            x = np.arange(len(data)).reshape(-1, 1)
            y = data['close'].values

            # Upper Channel (Resistance)
            upper_model = QuantileRegressor(quantile=self.upper_quantile, alpha=0, solver='highs-ds')
            upper_model.fit(x, y)
            upper_band = upper_model.predict(x)
            latest_upper_band = round(upper_band[-1], 4)

            # Lower Channel (Support)
            lower_model = QuantileRegressor(quantile=self.lower_quantile, alpha=0, solver='highs-ds')
            lower_model.fit(x, y)
            lower_band = lower_model.predict(x)
            latest_lower_band = round(lower_band[-1], 4)

            supports = [
                Level(
                    name="دعم القناة السعرية",
                    value=latest_lower_band,
                    level_type='support',
                    quality='Channel Bottom',
                    template_key='support_channel'
                )
            ]
            resistances = [
                Level(
                    name="مقاومة القناة السعرية",
                    value=latest_upper_band,
                    level_type='resistance',
                    quality='Channel Top',
                    template_key='resistance_channel'
                )
            ]

            return {'supports': supports, 'resistances': resistances}

        except Exception as e:
            logger.exception(f"Error during Quantile Channel analysis for timeframe {self.timeframe}")
            return {'supports': [], 'resistances': []}
