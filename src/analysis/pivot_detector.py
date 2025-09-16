import pandas as pd
from scipy.signal import find_peaks
from typing import List, Dict, Any

class PivotDetector:
    """
    A class to detect pivot points (highs and lows) in price data using a dynamic,
    ATR-based prominence calculation. This makes the detection adaptive to the
    volatility of different timeframes.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        # Default prominence multiplier, can be overridden by config
        self.prominence_multiplier = self.config.get('PIVOT_PROMINENCE_MULTIPLIER', 1.5)
        self.distance = self.config.get('PIVOT_DISTANCE', 5)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
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

        Args:
            df (pd.DataFrame): The market data with 'high', 'low', 'close' columns.

        Returns:
            Dict[str, List[Dict]]: A dictionary containing lists of high and low pivots.
            Each pivot is a dictionary with 'index' and 'price'.
        """
        if df.empty or len(df) < 20:
            return {'highs': [], 'lows': []}

        # Calculate dynamic prominence based on the average ATR
        # This makes the detection sensitive to the asset's recent volatility
        atr = self._calculate_atr(df)
        if atr.dropna().empty:
            # Fallback for very short dataframes
            dynamic_prominence = df['high'].std()
        else:
            dynamic_prominence = atr.mean() * self.prominence_multiplier

        # Find peaks (highs) and troughs (lows)
        high_indices, _ = find_peaks(df['high'], prominence=dynamic_prominence, distance=self.distance)
        low_indices, _ = find_peaks(-df['low'], prominence=dynamic_prominence, distance=self.distance)

        highs = [{'index': i, 'price': df['high'].iloc[i]} for i in high_indices]
        lows = [{'index': i, 'price': df['low'].iloc[i]} for i in low_indices]

        return {'highs': highs, 'lows': lows}
