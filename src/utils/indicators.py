import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Any

def find_swing_points(data: pd.DataFrame, lookback: int, prominence_multiplier: float = 0.5, atr_window: int = 14) -> Dict[str, List[Dict[str, Any]]]:
    """
    Finds all significant swing highs and lows in the lookback period.
    This version returns multiple points to be used for divergence detection.
    """
    recent_data = data.copy().iloc[-lookback:]

    # Use ATR for dynamic prominence
    atr = calculate_atr(recent_data, window=atr_window)
    dynamic_prominence = atr.mean() * prominence_multiplier if not atr.empty and atr.mean() > 0 else np.std(recent_data['high'] - recent_data['low']) * 0.1
    if dynamic_prominence <= 0: dynamic_prominence = 0.1

    high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=dynamic_prominence)
    low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=dynamic_prominence)

    result = {'highs': [], 'lows': []}
    for i in high_peaks_indices:
        result['highs'].append({'price': recent_data.iloc[i]['high'], 'index': i})
    for i in low_peaks_indices:
        result['lows'].append({'price': recent_data.iloc[i]['low'], 'index': i})

    abs_high_idx = recent_data['high'].idxmax()
    abs_low_idx = recent_data['low'].idxmin()
    if not any(p['index'] == recent_data.index.get_loc(abs_high_idx) for p in result['highs']):
         result['highs'].append({'price': recent_data.loc[abs_high_idx]['high'], 'index': recent_data.index.get_loc(abs_high_idx)})
    if not any(p['index'] == recent_data.index.get_loc(abs_low_idx) for p in result['lows']):
         result['lows'].append({'price': recent_data.loc[abs_low_idx]['low'], 'index': recent_data.index.get_loc(abs_low_idx)})

    result['highs'] = sorted(result['highs'], key=lambda x: x['index'])
    result['lows'] = sorted(result['lows'], key=lambda x: x['index'])

    return result

def detect_divergence(price_swings: List[Dict[str, Any]], indicator_series: pd.Series, type: str = 'bullish') -> bool:
    """Detects bullish or bearish divergence between price and an indicator."""
    if len(price_swings) < 2:
        return False

    last_swing = price_swings[-1]
    prev_swing = price_swings[-2]
    last_price = last_swing['price']
    prev_price = prev_swing['price']
    last_indicator = indicator_series.iloc[last_swing['index']]
    prev_indicator = indicator_series.iloc[prev_swing['index']]

    if type == 'bullish' and last_price < prev_price and last_indicator > prev_indicator:
        return True
    elif type == 'bearish' and last_price > prev_price and last_indicator < prev_indicator:
        return True
    return False

def calculate_sma(data: pd.DataFrame, window: int) -> pd.Series:
    if 'close' not in data.columns: raise ValueError("Input DataFrame must have a 'close' column.")
    return data['close'].rolling(window=window).mean()

def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    if 'close' not in data.columns: raise ValueError("Input DataFrame must have a 'close' column.")
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss; rs = rs.fillna(0)
    return 100 - (100 / (1 + rs))

def calculate_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    ema_fast = data['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({'macd': macd_line, 'signal_line': signal_line, 'histogram': histogram})

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, num_std_dev: int = 2) -> pd.DataFrame:
    middle_band = calculate_sma(data, window)
    std_dev = data['close'].rolling(window=window).std()
    upper_band = middle_band + (std_dev * num_std_dev)
    lower_band = middle_band - (std_dev * num_std_dev)
    return pd.DataFrame({'upper_band': upper_band, 'middle_band': middle_band, 'lower_band': lower_band})

def calculate_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    if not all(col in data.columns for col in ['high', 'low', 'close']): raise ValueError("Missing required columns")
    df = data.copy()
    df['H-L'] = df['high'] - df['low']
    df['H-C_prev'] = abs(df['high'] - df['close'].shift(1))
    df['L-C_prev'] = abs(df['low'] - df['close'].shift(1))
    tr = df[['H-L', 'H-C_prev', 'L-C_prev']].max(axis=1)
    return tr.ewm(alpha=1/window, adjust=False).mean()

def calculate_fib_levels(swing_high: float, swing_low: float, trend: str = 'up') -> Dict[str, float]:
    if swing_high <= swing_low: return {}
    swing_range = swing_high - swing_low
    levels, ratios = {}, [0.236, 0.382, 0.500, 0.618, 0.786, 0.886]
    for r in ratios: levels[f'fib_{int(r*1000)}'] = (swing_high - swing_range * r) if trend == 'up' else (swing_low + swing_range * r)
    return levels

def calculate_fib_extensions(swing_high: float, swing_low: float, trend: str = 'up') -> Dict[str, float]:
    if swing_high <= swing_low: return {}
    swing_range = swing_high - swing_low
    levels, ratios = {}, [1.272, 1.618, 2.000, 2.618, 3.618]
    for r in ratios: levels[f'ext_{int(r*1000)}'] = (swing_high + swing_range * r) if trend == 'up' else (swing_low - swing_range * r)
    return levels

def calculate_stochastic(data: pd.DataFrame, window: int = 14, smooth_k: int = 3) -> pd.DataFrame:
    low_min = data['low'].rolling(window=window).min()
    high_max = data['high'].rolling(window=window).max()
    stoch_k = 100 * ((data['close'] - low_min) / (high_max - low_min))
    stoch_d = stoch_k.rolling(window=smooth_k).mean()
    return pd.DataFrame({'stoch_k': stoch_k, 'stoch_d': stoch_d})

def calculate_obv(data: pd.DataFrame) -> pd.Series:
    return pd.Series((np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum(), name='obv')

def calculate_adx(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculates the Average Directional Index (ADX)."""
    df = data.copy()
    alpha = 1 / window

    # Correctly calculate and assign ATR first
    df['ATR'] = calculate_atr(df, window)

    # +DI, -DI
    df['+DM'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']), df['high'] - df['high'].shift(1), 0)
    df['+DM'] = np.where(df['+DM'] < 0, 0, df['+DM'])
    df['-DM'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)), df['low'].shift(1) - df['low'], 0)
    df['-DM'] = np.where(df['-DM'] < 0, 0, df['-DM'])

    df['+DI'] = 100 * (df['+DM'].ewm(alpha=alpha, adjust=False).mean() / df['ATR'])
    df['-DI'] = 100 * (df['-DM'].ewm(alpha=alpha, adjust=False).mean() / df['ATR'])

    # ADX
    df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / ((df['+DI'] + df['-DI']).replace(0, 1))) # Avoid division by zero
    adx = df['DX'].ewm(alpha=alpha, adjust=False).mean()
    return pd.Series(adx, name='adx')

def detect_trend_line_break(data: pd.DataFrame) -> bool:
    """Placeholder for a complex trend line detection algorithm."""
    return False

def calculate_zigzag(data: pd.DataFrame, threshold: float = 0.05) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculates swing points using the Zig Zag indicator methodology.
    Args:
        data: DataFrame with 'high', 'low', and 'close' columns. Assumes a monotonic increasing index.
        threshold: The percentage change required to reverse the trend. e.g., 0.05 for 5%.
    Returns:
        A dictionary with 'highs' and 'lows' lists, containing swing points.
    """
    if data.empty:
        return {'highs': [], 'lows': []}

    highs = []
    lows = []

    trend = 0  # 1 for up, -1 for down
    last_pivot_price = data['close'].iloc[0]
    last_pivot_idx = data.index[0]

    # Use 'high' and 'low' for comparison to find true peaks and troughs
    for i in range(1, len(data)):
        high_price = data['high'].iloc[i]
        low_price = data['low'].iloc[i]

        if trend == 0:
            if high_price > last_pivot_price * (1 + threshold):
                trend = 1
                # Not a real pivot yet, just establishing trend, but the start is a low
                lows.append({'price': last_pivot_price, 'index': last_pivot_idx})
                last_pivot_price = high_price
                last_pivot_idx = data.index[i]
            elif low_price < last_pivot_price * (1 - threshold):
                trend = -1
                # Not a real pivot yet, just establishing trend, but the start is a high
                highs.append({'price': last_pivot_price, 'index': last_pivot_idx})
                last_pivot_price = low_price
                last_pivot_idx = data.index[i]

        elif trend == 1:  # Uptrend, looking for a high
            if high_price > last_pivot_price:
                # New high in the current uptrend
                last_pivot_price = high_price
                last_pivot_idx = data.index[i]
            elif low_price < last_pivot_price * (1 - threshold):
                # Reversal confirmed, the last pivot was a high
                highs.append({'price': last_pivot_price, 'index': last_pivot_idx})
                trend = -1
                last_pivot_price = low_price
                last_pivot_idx = data.index[i]

        elif trend == -1:  # Downtrend, looking for a low
            if low_price < last_pivot_price:
                # New low in the current downtrend
                last_pivot_price = low_price
                last_pivot_idx = data.index[i]
            elif high_price > last_pivot_price * (1 + threshold):
                # Reversal confirmed, the last pivot was a low
                lows.append({'price': last_pivot_price, 'index': last_pivot_idx})
                trend = 1
                last_pivot_price = high_price
                last_pivot_idx = data.index[i]

    # Add the last unconfirmed pivot to the list
    if trend == 1:
        highs.append({'price': last_pivot_price, 'index': last_pivot_idx})
    elif trend == -1:
        lows.append({'price': last_pivot_price, 'index': last_pivot_idx})

    return {'highs': highs, 'lows': lows}
