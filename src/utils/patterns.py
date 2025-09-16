import pandas as pd

def is_bullish_engulfing(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """
    Checks for a Bullish Engulfing pattern.
    - Previous candle is bearish.
    - Current candle is bullish.
    - Current candle's body engulfs the previous candle's body.
    """
    if len(data) < 2:
        return False

    prev = data.iloc[-2]
    curr = data.iloc[-1]

    # Check for valid body sizes
    if abs(curr['open'] - curr['close']) < body_min_size or abs(prev['open'] - prev['close']) < body_min_size:
        return False

    is_prev_bearish = prev['close'] < prev['open']
    is_curr_bullish = curr['close'] > curr['open']

    if is_prev_bearish and is_curr_bullish:
        if curr['open'] < prev['close'] and curr['close'] > prev['open']:
            return True
    return False

def is_bearish_engulfing(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """
    Checks for a Bearish Engulfing pattern.
    - Previous candle is bullish.
    - Current candle is bearish.
    - Current candle's body engulfs the previous candle's body.
    """
    if len(data) < 2:
        return False

    prev = data.iloc[-2]
    curr = data.iloc[-1]

    # Check for valid body sizes
    if abs(curr['open'] - curr['close']) < body_min_size or abs(prev['open'] - prev['close']) < body_min_size:
        return False

    is_prev_bullish = prev['close'] > prev['open']
    is_curr_bearish = curr['close'] < curr['open']

    if is_prev_bullish and is_curr_bearish:
        if curr['open'] > prev['close'] and curr['close'] < prev['open']:
            return True
    return False

def is_hammer(data: pd.DataFrame, body_ratio: float = 0.3, lower_wick_ratio: float = 0.6) -> bool:
    """
    Checks for a Hammer pattern (bullish reversal).
    - Small body at the top of the candle.
    - Long lower wick.
    - Very small or no upper wick.
    """
    if len(data) < 1:
        return False

    candle = data.iloc[-1]
    body_size = abs(candle['open'] - candle['close'])
    candle_range = candle['high'] - candle['low']

    if candle_range == 0:
        return False

    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']

    # Conditions for a hammer
    is_small_body = body_size <= body_ratio * candle_range
    is_long_lower_wick = lower_wick >= lower_wick_ratio * candle_range
    is_small_upper_wick = upper_wick <= (1 - lower_wick_ratio - body_ratio + 0.1) * candle_range # Allow for small tolerance

    return is_small_body and is_long_lower_wick and is_small_upper_wick

def is_doji(data: pd.DataFrame, body_threshold: float = 0.05) -> bool:
    """
    Checks for a Doji pattern (indecision).
    - Body is extremely small (open and close are very close).
    """
    if len(data) < 1:
        return False

    candle = data.iloc[-1]
    body_size = abs(candle['open'] - candle['close'])
    candle_range = candle['high'] - candle['low']

    if candle_range == 0:
        # If there's no range, it can't be a doji in a meaningful way
        return False

    return body_size / candle_range < body_threshold

def get_candlestick_pattern(data: pd.DataFrame) -> str:
    """
    Identifies the most prominent recent candlestick pattern.
    Checks for patterns on the last one or two candles.
    """
    if is_bullish_engulfing(data):
        return "Bullish Engulfing"
    if is_bearish_engulfing(data):
        return "Bearish Engulfing"
    if is_hammer(data):
        return "Hammer"
    if is_doji(data):
        return "Doji"
    return "No Pattern"
