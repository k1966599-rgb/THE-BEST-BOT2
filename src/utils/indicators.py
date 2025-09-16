import pandas as pd

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
