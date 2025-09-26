import pandas as pd

def is_bullish_engulfing(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """Checks for a Bullish Engulfing pattern."""
    if len(data) < 2: return False
    prev, curr = data.iloc[-2], data.iloc[-1]
    if abs(curr['open'] - curr['close']) < body_min_size or abs(prev['open'] - prev['close']) < body_min_size: return False
    is_prev_bearish = prev['close'] < prev['open']
    is_curr_bullish = curr['close'] > curr['open']
    if is_prev_bearish and is_curr_bullish and curr['open'] < prev['close'] and curr['close'] > prev['open']:
        return True
    return False

def is_bearish_engulfing(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """Checks for a Bearish Engulfing pattern."""
    if len(data) < 2: return False
    prev, curr = data.iloc[-2], data.iloc[-1]
    if abs(curr['open'] - curr['close']) < body_min_size or abs(prev['open'] - prev['close']) < body_min_size: return False
    is_prev_bullish = prev['close'] > prev['open']
    is_curr_bearish = curr['close'] < curr['open']
    if is_prev_bullish and is_curr_bearish and curr['open'] > prev['close'] and curr['close'] < prev['open']:
        return True
    return False

def is_hammer(candle: pd.Series, body_ratio: float = 0.3, lower_wick_ratio: float = 0.6) -> bool:
    """Checks if a single candle is a Hammer."""
    body_size = abs(candle['open'] - candle['close'])
    candle_range = candle['high'] - candle['low']
    if candle_range == 0: return False
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    return body_size <= body_ratio * candle_range and lower_wick >= lower_wick_ratio * candle_range and upper_wick <= (1 - lower_wick_ratio - body_ratio + 0.1) * candle_range

def is_shooting_star(candle: pd.Series, body_ratio: float = 0.3, upper_wick_ratio: float = 0.6) -> bool:
    """Checks if a single candle is a Shooting Star."""
    body_size = abs(candle['open'] - candle['close'])
    candle_range = candle['high'] - candle['low']
    if candle_range == 0: return False
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    return body_size <= body_ratio * candle_range and upper_wick >= upper_wick_ratio * candle_range and lower_wick <= (1 - upper_wick_ratio - body_ratio + 0.1) * candle_range

def is_doji(candle: pd.Series, body_threshold: float = 0.05) -> bool:
    """Checks if a single candle is a Doji."""
    candle_range = candle['high'] - candle['low']
    if candle_range == 0: return False
    return abs(candle['open'] - candle['close']) / candle_range < body_threshold

def is_piercing_pattern(data: pd.DataFrame) -> bool:
    """Checks for a Piercing Pattern (bullish reversal)."""
    if len(data) < 2: return False
    prev, curr = data.iloc[-2], data.iloc[-1]
    is_prev_bearish = prev['close'] < prev['open']
    is_curr_bullish = curr['close'] > curr['open']
    mid_point = (prev['open'] + prev['close']) / 2
    if is_prev_bearish and is_curr_bullish and curr['open'] < prev['low'] and curr['close'] > mid_point and curr['close'] < prev['open']:
        return True
    return False

def is_dark_cloud_cover(data: pd.DataFrame) -> bool:
    """Checks for a Dark Cloud Cover pattern (bearish reversal)."""
    if len(data) < 2: return False
    prev, curr = data.iloc[-2], data.iloc[-1]
    is_prev_bullish = prev['close'] > prev['open']
    is_curr_bearish = curr['close'] < curr['open']
    mid_point = (prev['open'] + prev['close']) / 2
    if is_prev_bullish and is_curr_bearish and curr['open'] > prev['high'] and curr['close'] < mid_point and curr['close'] > prev['open']:
        return True
    return False

def is_morning_star(data: pd.DataFrame) -> bool:
    """Checks for a Morning Star pattern (bullish reversal)."""
    if len(data) < 3: return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]
    is_c1_bearish = c1['close'] < c1['open']
    is_c2_small_body = abs(c2['open'] - c2['close']) < (c1['open'] - c1['close'])
    is_c3_bullish = c3['close'] > c3['open']
    closes_in_top_half = c3['close'] > (c1['open'] + c1['close']) / 2
    if is_c1_bearish and is_c2_small_body and is_c3_bullish and closes_in_top_half:
        return True
    return False

def is_evening_star(data: pd.DataFrame) -> bool:
    """Checks for an Evening Star pattern (bearish reversal)."""
    if len(data) < 3: return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]
    is_c1_bullish = c1['close'] > c1['open']
    is_c2_small_body = abs(c2['open'] - c2['close']) < (c1['close'] - c1['open'])
    is_c3_bearish = c3['close'] < c3['open']
    closes_in_bottom_half = c3['close'] < (c1['open'] + c1['close']) / 2
    if is_c1_bullish and is_c2_small_body and is_c3_bearish and closes_in_bottom_half:
        return True
    return False

def get_candlestick_pattern(data: pd.DataFrame) -> str:
    """
    Identifies the most prominent recent candlestick pattern.
    Checks for patterns on the last one, two, or three candles.
    Priority is given to more complex (and often more reliable) patterns.
    """
    # 3-candle patterns
    if is_morning_star(data): return "Morning Star"
    if is_evening_star(data): return "Evening Star"

    # 2-candle patterns
    if is_bullish_engulfing(data): return "Bullish Engulfing"
    if is_bearish_engulfing(data): return "Bearish Engulfing"
    if is_piercing_pattern(data): return "Piercing Pattern"
    if is_dark_cloud_cover(data): return "Dark Cloud Cover"

    # 1-candle patterns
    if len(data) > 0:
        last_candle = data.iloc[-1]
        if is_hammer(last_candle): return "Hammer"
        if is_shooting_star(last_candle): return "Shooting Star"
        if is_doji(last_candle): return "Doji"

    return "No Pattern"