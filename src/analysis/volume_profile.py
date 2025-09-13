import pandas as pd
import numpy as np
from typing import Dict, List
from .base_analysis import BaseAnalysis
from .data_models import Level

class VolumeProfileAnalysis(BaseAnalysis):
    """
    Analyzes the volume profile of a given market data to find significant
    support and resistance zones based on high-volume nodes (HVNs) and the
    Point of Control (POC).
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        self.bins = 50

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Level]]:
        if df.empty or 'volume' not in df.columns:
            return {'supports': [], 'resistances': []}

        min_price = df['low'].min()
        max_price = df['high'].max()
        price_bins = np.linspace(min_price, max_price, self.bins)

        volume_by_price = np.zeros(self.bins)
        for _, row in df.iterrows():
            price_index = np.searchsorted(price_bins, row['close']) -1
            if 0 <= price_index < self.bins:
                volume_by_price[price_index] += row['volume']

        if np.sum(volume_by_price) == 0:
            return {'supports': [], 'resistances': []}

        poc_index = np.argmax(volume_by_price)
        poc_price = price_bins[poc_index]

        average_volume = np.mean(volume_by_price)
        hvn_indices = np.where(volume_by_price > average_volume * 1.75)[0] # Lowered multiplier for more results

        supports = []
        resistances = []
        current_price = df['close'].iloc[-1]

        poc_level = Level(
            name="Volume Profile POC",
            value=round(poc_price, 4),
            level_type='support' if poc_price < current_price else 'resistance',
            quality='POC'
        )
        if poc_price < current_price:
            supports.append(poc_level)
        else:
            resistances.append(poc_level)

        for idx in hvn_indices:
            if idx == poc_index: continue
            hvn_price = price_bins[idx]
            hvn_level = Level(
                name="High Volume Node",
                value=round(hvn_price, 4),
                level_type='support' if hvn_price < current_price else 'resistance',
                quality='HVN'
            )
            if hvn_price < current_price:
                supports.append(hvn_level)
            else:
                resistances.append(hvn_level)

        return {'supports': supports, 'resistances': resistances}
