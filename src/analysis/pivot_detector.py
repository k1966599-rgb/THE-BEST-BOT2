import pandas as pd
from scipy.signal import find_peaks
from typing import List, Dict, Any
from .base_analysis import BaseAnalysis

class PivotDetector(BaseAnalysis):
    """
    A class to detect pivot points (highs and lows) in price data using a dynamic,
    ATR-based prominence calculation. This makes the detection adaptive to the
    volatility of different timeframes.
    """
    def __init__(self, config: dict, timeframe: str):
        super().__init__(config, timeframe)

        self.prominence_multiplier = self.params.get('pivot_atr_multiplier', 1.5)
        self.distance = self.params.get('pivot_distance', 5)
        self.atr_period = self.config.get('ATR_PERIOD', 14)

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculates the Average True Range (ATR)."""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(window=period).mean()

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        Detects pivot highs and lows in the given DataFrame.
        """
        if df.empty or len(df) < 20:
            return {'highs': [], 'lows': []}

        atr = self._calculate_atr(df, period=self.atr_period)
        if atr.dropna().empty:
            dynamic_prominence = df['high'].std()
        else:
            dynamic_prominence = atr.mean() * self.prominence_multiplier

        high_indices, _ = find_peaks(df['high'], prominence=dynamic_prominence, distance=self.distance)
        low_indices, _ = find_peaks(-df['low'], prominence=dynamic_prominence, distance=self.distance)

        highs = [{'index': i, 'price': df['high'].iloc[i]} for i in high_indices]
        lows = [{'index': i, 'price': df['low'].iloc[i]} for i in low_indices]

        return {'highs': highs, 'lows': lows}
