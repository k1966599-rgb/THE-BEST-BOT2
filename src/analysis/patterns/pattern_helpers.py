import numpy as np
import pandas as pd
from typing import Dict, List

def calculate_dynamic_confidence(df: pd.DataFrame, config: dict, base_confidence: int, is_bullish: bool) -> int:
    """
    Calculates a dynamic confidence score based on volume, trend strength (ADX), and momentum (RSI).
    """
    if len(df) == 0: return base_confidence

    confidence = base_confidence
    latest_data = df.iloc[-1]

    # Volume Confirmation
    try:
        breakout_volume = latest_data['volume']
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
        if breakout_volume > avg_volume * 1.5:
            confidence += 10
    except (KeyError, IndexError):
        pass

    # ADX Confirmation
    try:
        adx_key = f"ADX_{config.get('ADX_PERIOD', 14)}"
        if adx_key in df.columns:
            adx_value = latest_data[adx_key]
            if adx_value > 25:
                confidence += 10
    except (KeyError, IndexError):
        pass

    # RSI Confirmation
    try:
        rsi_key = f"RSI_{config.get('RSI_PERIOD', 14)}"
        if rsi_key in df.columns:
            rsi_value = latest_data[rsi_key]
            if is_bullish and rsi_value < 75:
                confidence += 5
            elif not is_bullish and rsi_value > 25:
                confidence += 5
    except (KeyError, IndexError):
        pass

    return min(confidence, 98)

def find_trend_line(x_coords: List[int], y_coords: List[float]) -> Dict[str, float]:
    """
    Finds the line of best fit for a series of points using linear regression.
    Returns the slope and intercept of the line.
    """
    if not x_coords or not y_coords or len(x_coords) != len(y_coords):
        return {'slope': 0, 'intercept': 0}

    # Using numpy's polyfit for linear regression (degree 1)
    slope, intercept = np.polyfit(x_coords, y_coords, 1)
    return {'slope': slope, 'intercept': intercept}
