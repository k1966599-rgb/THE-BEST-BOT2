import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List

def find_swing_points(data: pd.DataFrame, lookback: int, prominence: float = 0.1) -> Dict[str, float]:
    """
    Finds the most recent significant swing high and swing low.

    Args:
        data (pd.DataFrame): DataFrame with 'high' and 'low' columns.
        lookback (int): The number of recent candles to consider.
        prominence (float): The required prominence of the peaks. This helps filter out minor fluctuations.

    Returns:
        Dict[str, float]: A dictionary containing the 'swing_high' and 'swing_low' prices.
    """
    recent_data = data.iloc[-lookback:]

    # Find peaks (swing highs) in the 'high' series
    high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=prominence)

    # Find peaks in the inverted 'low' series to find troughs (swing lows)
    low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=prominence)

    if high_peaks_indices.size > 0:
        # Get the price of the most recent swing high
        most_recent_high_index = high_peaks_indices[-1]
        swing_high = recent_data['high'].iloc[most_recent_high_index]
    else:
        # Fallback to simple max if no prominent peak is found
        swing_high = recent_data['high'].max()

    if low_peaks_indices.size > 0:
        # Get the price of the most recent swing low
        most_recent_low_index = low_peaks_indices[-1]
        swing_low = recent_data['low'].iloc[most_recent_low_index]
    else:
        # Fallback to simple min if no prominent peak is found
        swing_low = recent_data['low'].min()

    return {'swing_high': swing_high, 'swing_low': swing_low}


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

def calculate_fib_extensions(swing_high: float, swing_low: float) -> List[float]:
    """
    Calculates Fibonacci extension levels for take-profit targets.

    Args:
        swing_high (float): The price of the swing high.
        swing_low (float): The price of the swing low.

    Returns:
        List[float]: A list of potential take-profit target prices.
    """
    if swing_high <= swing_low:
        return []

    swing_range = swing_high - swing_low

    # Common Fibonacci extension levels
    # For an uptrend, targets are above the swing high
    target1 = swing_high + swing_range * 1.618
    target2 = swing_high + swing_range * 2.618

    # For a downtrend, targets would be below the swing low, but we'll focus on uptrend targets for now.
    # The logic in the strategy will determine when to use these.

    return [target1, target2]
