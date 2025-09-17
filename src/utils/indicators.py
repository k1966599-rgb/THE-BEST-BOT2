import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Any

def find_swing_points(data: pd.DataFrame, lookback: int, prominence: float = 0.1) -> Dict[str, Dict[str, Any]]:
    """
    Finds the most recent significant swing high and swing low.

    Args:
        data (pd.DataFrame): DataFrame with 'high', 'low', and 'timestamp' columns.
        lookback (int): The number of recent candles to consider.
        prominence (float): The required prominence of the peaks. This helps filter out minor fluctuations.

    Returns:
        A dictionary containing info about the swing high and low.
        e.g. {'swing_high': {'price': 123.45, 'timestamp': 1678886400000}, ...}
    """
    recent_data = data.iloc[-lookback:].copy()
    # Ensure timestamp is in a usable format
    recent_data['datetime'] = pd.to_datetime(recent_data['timestamp'], unit='ms')

    high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=prominence)
    low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=prominence)

    result = {
        'swing_high': {'price': None, 'timestamp': None},
        'swing_low': {'price': None, 'timestamp': None}
    }

    if high_peaks_indices.size > 0:
        most_recent_high_index = high_peaks_indices[-1]
        result['swing_high']['price'] = recent_data['high'].iloc[most_recent_high_index]
        result['swing_high']['timestamp'] = recent_data['timestamp'].iloc[most_recent_high_index]
    else:
        # Fallback to simple max
        idx = recent_data['high'].idxmax()
        result['swing_high']['price'] = recent_data['high'].loc[idx]
        result['swing_high']['timestamp'] = recent_data['timestamp'].loc[idx]

    if low_peaks_indices.size > 0:
        most_recent_low_index = low_peaks_indices[-1]
        result['swing_low']['price'] = recent_data['low'].iloc[most_recent_low_index]
        result['swing_low']['timestamp'] = recent_data['timestamp'].iloc[most_recent_low_index]
    else:
        # Fallback to simple min
        idx = recent_data['low'].idxmin()
        result['swing_low']['price'] = recent_data['low'].loc[idx]
        result['swing_low']['timestamp'] = recent_data['timestamp'].loc[idx]

    return result


def calculate_sma(data: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculates the Simple Moving Average (SMA).

    Args:
        data (pd.DataFrame): DataFrame with a 'close' column.
        window (int): The period for the moving average.

    Returns:
        pd.Series: A pandas Series containing the SMA values.
    """
    if 'close' not in data.columns:
        raise ValueError("Input DataFrame must have a 'close' column.")
    return data['close'].rolling(window=window).mean()

def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Calculates the Relative Strength Index (RSI).

    Args:
        data (pd.DataFrame): DataFrame with a 'close' column.
        window (int): The period for the RSI calculation.

    Returns:
        pd.Series: A pandas Series containing the RSI values.
    """
    if 'close' not in data.columns:
        raise ValueError("Input DataFrame must have a 'close' column.")

    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    # Avoid division by zero
    rs = gain / loss
    rs = rs.fillna(0) # Fill NaNs in rs, which can happen if loss is 0

    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(data: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculates the Exponential Moving Average (EMA).

    Args:
        data (pd.DataFrame): DataFrame with a 'close' column.
        window (int): The period for the moving average.

    Returns:
        pd.Series: A pandas Series containing the EMA values.
    """
    if 'close' not in data.columns:
        raise ValueError("Input DataFrame must have a 'close' column.")
    return data['close'].ewm(span=window, adjust=False).mean()

def calculate_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    """
    Calculates the Moving Average Convergence Divergence (MACD).

    Args:
        data (pd.DataFrame): DataFrame with a 'close' column.
        fast_period (int): The window for the fast EMA.
        slow_period (int): The window for the slow EMA.
        signal_period (int): The window for the signal line EMA.

    Returns:
        pd.DataFrame: A DataFrame with 'macd', 'signal_line', and 'histogram' columns.
    """
    ema_fast = calculate_ema(data, fast_period)
    ema_slow = calculate_ema(data, slow_period)

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    macd_df = pd.DataFrame({
        'macd': macd_line,
        'signal_line': signal_line,
        'histogram': histogram
    })
    return macd_df

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, num_std_dev: int = 2) -> pd.DataFrame:
    """
    Calculates Bollinger Bands.

    Args:
        data (pd.DataFrame): DataFrame with a 'close' column.
        window (int): The moving average period.
        num_std_dev (int): The number of standard deviations.

    Returns:
        pd.DataFrame: A DataFrame with 'upper_band', 'middle_band', 'lower_band'.
    """
    if 'close' not in data.columns:
        raise ValueError("Input DataFrame must have a 'close' column.")

    middle_band = calculate_sma(data, window)
    std_dev = data['close'].rolling(window=window).std()

    upper_band = middle_band + (std_dev * num_std_dev)
    lower_band = middle_band - (std_dev * num_std_dev)

    bb_df = pd.DataFrame({
        'upper_band': upper_band,
        'middle_band': middle_band,
        'lower_band': lower_band
    })
    return bb_df

def calculate_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Calculates the Average True Range (ATR).

    Args:
        data (pd.DataFrame): DataFrame with 'high', 'low', 'close' columns.
        window (int): The period for the ATR calculation.

    Returns:
        pd.Series: A pandas Series containing the ATR values.
    """
    if not all(col in data.columns for col in ['high', 'low', 'close']):
        raise ValueError("Input DataFrame must have 'high', 'low', and 'close' columns.")

    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/window, adjust=False).mean()

    return atr

def calculate_fib_levels(swing_high: float, swing_low: float, trend: str = 'up') -> Dict[str, float]:
    """
    Calculates Fibonacci retracement levels based on the trend direction.
    """
    if swing_high <= swing_low:
        return {}

    swing_range = swing_high - swing_low
    levels = {}
    ratios = [0.236, 0.382, 0.500, 0.618, 0.786, 0.886]

    if trend == 'up':
        # In an uptrend, we are looking for a pullback (downward correction).
        # Levels are measured from the high down. 0.0 is at the high, 1.0 is at the low.
        for ratio in ratios:
            levels[f'fib_{int(ratio*1000)}'] = swing_high - swing_range * ratio
    else: # downtrend
        # In a downtrend, we are looking for a pullback (upward correction).
        # Levels are measured from the low up. 0.0 is at the low, 1.0 is at the high.
        for ratio in ratios:
            levels[f'fib_{int(ratio*1000)}'] = swing_low + swing_range * ratio

    return levels

def calculate_fib_extensions(swing_high: float, swing_low: float, trend: str = 'up') -> Dict[str, float]:
    """
    Calculates Fibonacci extension levels for take-profit targets based on trend.
    """
    if swing_high <= swing_low:
        return {}

    swing_range = swing_high - swing_low
    levels = {}
    ratios = [1.272, 1.618, 2.000, 2.618, 3.618]

    if trend == 'up':
        # In an uptrend, targets are above the swing high.
        for ratio in ratios:
            levels[f'ext_{int(ratio*1000)}'] = swing_high + swing_range * ratio
    else: # downtrend
        # In a downtrend, targets are below the swing low.
        for ratio in ratios:
            levels[f'ext_{int(ratio*1000)}'] = swing_low - swing_range * ratio

    return levels

def detect_trend_line_break(data: pd.DataFrame) -> bool:
    """
    Placeholder for a complex trend line detection algorithm.
    A real implementation would involve linear regression on swing points.
    For now, this is a placeholder and will not affect the analysis.
    """
    # Returning False as this is a placeholder for a future feature.
    return False
