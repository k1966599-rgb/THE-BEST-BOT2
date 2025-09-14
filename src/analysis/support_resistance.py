import pandas as pd
import numpy as np
from typing import Dict, List
from .base_analysis import BaseAnalysis
import logging
from .patterns.pattern_utils import get_pivots, cluster_levels
from .data_models import Level

logger = logging.getLogger(__name__)

class SupportResistanceAnalysis(BaseAnalysis):
    """
    Analyzes support and resistance levels based on pivot points.
    This class identifies pivot highs and lows, clusters them, and also
    identifies the most significant historical S/R level.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('SR_LOOKBACK', self.config.get('SR_LOOKBACK', 200))
        self.cluster_percent = overrides.get('SR_CLUSTER_PERCENT', self.config.get('SR_CLUSTER_PERCENT', 0.5))

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        if len(df) < self.lookback:
            return {'supports': [], 'resistances': []}

        data = df.tail(self.lookback)
        current_price = data['close'].iloc[-1]

        try:
            highs, lows = get_pivots(data)
            if not highs or not lows:
                return {'supports': [], 'resistances': []}

            support_levels_raw = cluster_levels([l['price'] for l in lows if l['price'] < current_price], self.cluster_percent)
            resistance_levels_raw = cluster_levels([h['price'] for h in highs if h['price'] > current_price], self.cluster_percent)

            supports = [Level(name="دعم ثانوي", value=round(s, 4), level_type='support', quality='Secondary') for s in support_levels_raw]
            resistances = [Level(name="مقاومة ثانوية", value=round(r, 4), level_type='resistance', quality='Secondary') for r in resistance_levels_raw]

            if support_levels_raw:
                general_support = min(support_levels_raw)
                supports.append(Level(name="دعم عام سابق", value=round(general_support, 4), level_type='support', quality='Historic'))

            if resistance_levels_raw:
                general_resistance = max(resistance_levels_raw)
                resistances.append(Level(name="مقاومة عامة سابقة", value=round(general_resistance, 4), level_type='resistance', quality='Historic'))

            return {'supports': supports, 'resistances': resistances}

        except Exception as e:
            logger.exception("Error during S/R analysis")
            return {'supports': [], 'resistances': []}
