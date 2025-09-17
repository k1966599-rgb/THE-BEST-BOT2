import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Any

def find_swing_points(data: pd.DataFrame, lookback: int, atr_window: int = 14, prominence_multiplier: float = 1.5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Finds all significant swing highs and lows in the lookback period using dynamic
    prominence based on the Average True Range (ATR).

    Args:
        data (pd.DataFrame): DataFrame with 'high', 'low', 'close', and 'timestamp' columns.
        lookback (int): The number of recent candles to consider.
        atr_window (int): The window to use for ATR calculation.
        prominence_multiplier (float): The multiplier for ATR to determine prominence.

    Returns:
        A dictionary containing lists of swing high and swing low points.
        e.g., {'swing_highs': [{'price': 123, 'timestamp': ...}, ...], 'swing_lows': [...]}
    """
    recent_data = data.iloc[-lookback:].copy()
    recent_data['datetime'] = pd.to_datetime(recent_data['timestamp'], unit='ms')

    atr = calculate_atr(recent_data, window=atr_window)
    dynamic_prominence = atr.mean() * prominence_multiplier if not atr.empty else 0.1

    high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=dynamic_prominence)
    low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=dynamic_prominence)

    result = {'swing_highs': [], 'swing_lows': []}

    if high_peaks_indices.size > 0:
        for i in high_peaks_indices:
            point = recent_data.iloc[i]
            result['swing_highs'].append({'price': point['high'], 'timestamp': point['timestamp'], 'index': data.index[0] + i})
    else:
        # Fallback to simple max if no peaks found
        idx = recent_data['high'].idxmax()
        point = recent_data.loc[idx]
        result['swing_highs'].append({'price': point['high'], 'timestamp': point['timestamp'], 'index': idx})


    if low_peaks_indices.size > 0:
        for i in low_peaks_indices:
            point = recent_data.iloc[i]
            result['swing_lows'].append({'price': point['low'], 'timestamp': point['timestamp'], 'index': data.index[0] + i})
    else:
        # Fallback to simple min
        idx = recent_data['low'].idxmin()
        point = recent_data.loc[idx]
        result['swing_lows'].append({'price': point['low'], 'timestamp': point['timestamp'], 'index': idx})


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

def detect_trend_line_break(data: pd.DataFrame, swing_points: List[Dict[str, Any]], lookback_points: int = 3, line_type: str = 'support') -> bool:
    """
    Detects a break of a trend line drawn through recent swing points.

    Args:
        data (pd.DataFrame): The full DataFrame of price data.
        swing_points (List[Dict[str, Any]]): A list of swing points (highs or lows).
        lookback_points (int): The number of recent swing points to use for the trend line.
        line_type (str): 'support' for trend line through lows, 'resistance' for highs.

    Returns:
        bool: True if the most recent close has broken the trend line, False otherwise.
    """
    if len(swing_points) < 2:
        return False

    # Use the last `lookback_points` swing points to draw the line
    relevant_points = swing_points[-lookback_points:]
    if len(relevant_points) < 2:
        return False

    # Prepare data for linear regression
    indices = np.array([p['index'] for p in relevant_points])
    prices = np.array([p['price'] for p in relevant_points])

    # Fit a line (degree 1 polynomial) to the points
    # The result, 'coeffs', contains the slope and y-intercept
    try:
        coeffs = np.polyfit(indices, prices, 1)
    except np.linalg.LinAlgError:
        # Could happen if points are perfectly vertical, etc.
        return False

    trend_line_func = np.poly1d(coeffs)

    # Get the index of the latest candle
    latest_index = data.index[-1]
    latest_close = data.iloc[-1]['close']

    # Calculate the trend line's value at the latest index
    trend_line_value_now = trend_line_func(latest_index)

    if line_type == 'support':
        # A support break happens when the close is below the trend line
        return latest_close < trend_line_value_now
    elif line_type == 'resistance':
        # A resistance break happens when the close is above the trend line
        return latest_close > trend_line_value_now
    else:
        return False

def calculate_volume_profile(data: pd.DataFrame, lookback: int, bins: int = 20) -> float:
    """
    Calculates a simple volume profile and finds the Point of Control (POC).

    Args:
        data (pd.DataFrame): DataFrame with 'close' and 'volume' columns.
        lookback (int): The number of recent candles to consider.
        bins (int): The number of price bins to create.

    Returns:
        float: The price level of the Point of Control (POC), or 0 if it cannot be calculated.
    """
    if len(data) < lookback:
        return 0

    recent_data = data.iloc[-lookback:]

    price_range = recent_data['high'].max() - recent_data['low'].min()
    if price_range == 0:
        return 0

    # Create price bins
    price_bins = np.linspace(recent_data['low'].min(), recent_data['high'].max(), bins + 1)

    # Assign each candle's close price to a bin
    recent_data['price_bin'] = pd.cut(recent_data['close'], bins=price_bins, labels=False, include_lowest=True)

    # Group by price bin and sum the volume
    volume_by_bin = recent_data.groupby('price_bin')['volume'].sum()

    if volume_by_bin.empty:
        return 0

    # Find the bin with the maximum volume (Point of Control)
    poc_bin_index = volume_by_bin.idxmax()

    # Calculate the price corresponding to the center of the POC bin
    poc_price = (price_bins[poc_bin_index] + price_bins[poc_bin_index + 1]) / 2

    return poc_price
