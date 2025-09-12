import pandas as pd
import numpy as np
from typing import Dict, List
from .base_analysis import BaseAnalysis
import logging
from .patterns.pattern_utils import get_pivots
from .data_models import Level

logger = logging.getLogger(__name__)

class SupportResistanceAnalysis(BaseAnalysis):
    """Analyzes support and resistance levels based on pivot points.

    This class identifies pivot highs and lows in the price data, clusters
    them to find significant levels, and then classifies them as support or
    resistance relative to the current price.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        """Initializes the SupportResistanceAnalysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed. Defaults to '1h'.
        """
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('SR_LOOKBACK', self.config.get('SR_LOOKBACK', 200))
        self.cluster_percent = overrides.get('SR_CLUSTER_PERCENT', self.config.get('SR_CLUSTER_PERCENT', 0.5))

    def _cluster_levels(self, levels: List[float]) -> List[float]:
        """Clusters a list of price levels into significant groups.

        Args:
            levels (List[float]): A list of price levels to be clustered.

        Returns:
            List[float]: A list of clustered level values (the mean of each
            cluster).
        """
        if not levels: return []
        levels.sort()
        clusters, current_cluster = [], [levels[0]]
        for level in levels[1:]:
            if (level - np.mean(current_cluster)) / np.mean(current_cluster) * 100 <= self.cluster_percent:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        clusters.append(np.mean(current_cluster))
        return clusters

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        """Identifies and clusters support and resistance levels.

        This method finds pivot points, clusters them, and then creates
        standardized Level objects for supports (below current price) and
        resistances (above current price).

        Args:
            df (pd.DataFrame): The DataFrame containing market data.

        Returns:
            Dict[str, List[Level]]: A dictionary containing lists of support
            and resistance Level objects.
        """
        if len(df) < self.lookback:
            return {'supports': [], 'resistances': []}

        data = df.tail(self.lookback)
        current_price = data['close'].iloc[-1]

        try:
            highs, lows = get_pivots(data)
            if not highs or not lows:
                return {'supports': [], 'resistances': []}

            support_levels_raw = self._cluster_levels([l['price'] for l in lows if l['price'] < current_price])
            resistance_levels_raw = self._cluster_levels([h['price'] for h in highs if h['price'] > current_price])

            supports = [Level(name="دعم سابق", value=round(s, 4), level_type='support', quality='ثانوي') for s in support_levels_raw]
            resistances = [Level(name="مقاومة سابقة", value=round(r, 4), level_type='resistance', quality='ثانوي') for r in resistance_levels_raw]

            return {'supports': supports, 'resistances': resistances}

        except Exception as e:
            logger.exception("Error during S/R analysis")
            return {'supports': [], 'resistances': []}
