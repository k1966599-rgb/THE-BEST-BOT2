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

def is_morning_star(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """
    Checks for a Morning Star pattern (bullish reversal, 3-candle pattern).
    1. First candle is a significant bearish candle.
    2. Second candle is a small-bodied candle (a star) that gaps down.
    3. Third candle is a bullish candle that closes well into the first candle's body.
    """
    if len(data) < 3:
        return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]

    # Rule 1: First candle is bearish
    is_c1_bearish = c1['close'] < c1['open']
    c1_body = abs(c1['open'] - c1['close'])

    # Rule 2: Second candle has a small body and ideally gaps down
    c2_body = abs(c2['open'] - c2['close'])
    gaps_down = max(c2['open'], c2['close']) < c1['close']

    # Rule 3: Third candle is bullish and closes above the midpoint of the first candle
    is_c3_bullish = c3['close'] > c3['open']
    closes_in_c1_body = c3['close'] > (c1['open'] + c1['close']) / 2

    return is_c1_bearish and c1_body > body_min_size and c2_body < (c1_body * 0.5) and gaps_down and is_c3_bullish and closes_in_c1_body

def is_evening_star(data: pd.DataFrame, body_min_size: float = 0.0001) -> bool:
    """
    Checks for an Evening Star pattern (bearish reversal, 3-candle pattern).
    1. First candle is a significant bullish candle.
    2. Second candle is a small-bodied candle (a star) that gaps up.
    3. Third candle is a bearish candle that closes well into the first candle's body.
    """
    if len(data) < 3:
        return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]

    # Rule 1: First candle is bullish
    is_c1_bullish = c1['close'] > c1['open']
    c1_body = abs(c1['open'] - c1['close'])

    # Rule 2: Second candle has a small body and ideally gaps up
    c2_body = abs(c2['open'] - c2['close'])
    gaps_up = min(c2['open'], c2['close']) > c1['close']

    # Rule 3: Third candle is bearish and closes below the midpoint of the first candle
    is_c3_bearish = c3['close'] < c3['open']
    closes_in_c1_body = c3['close'] < (c1['open'] + c1['close']) / 2

    return is_c1_bullish and c1_body > body_min_size and c2_body < (c1_body * 0.5) and gaps_up and is_c3_bearish and closes_in_c1_body

def is_three_white_soldiers(data: pd.DataFrame) -> bool:
    """
    Checks for Three White Soldiers pattern (strong bullish).
    - Three consecutive long bullish candles.
    - Each opens within the previous candle's body.
    - Each closes at a new high.
    """
    if len(data) < 3:
        return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]

    # All three are bullish
    if not (c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] > c3['open']):
        return False

    # Each opens within the previous body
    opens_in_body = (c2['open'] > c1['open'] and c2['open'] < c1['close']) and \
                    (c3['open'] > c2['open'] and c3['open'] < c2['close'])

    # Each closes at a new high
    closes_higher = (c2['close'] > c1['close']) and (c3['close'] > c2['close'])

    # Optional: ensure they are not too short and don't have long upper wicks
    c1_body = c1['close'] - c1['open']
    c2_body = c2['close'] - c2['open']
    c3_body = c3['close'] - c3['open']
    no_long_wicks = (c1['high'] - c1['close']) < c1_body and \
                    (c2['high'] - c2['close']) < c2_body and \
                    (c3['high'] - c3['close']) < c3_body

    return opens_in_body and closes_higher and no_long_wicks

def is_three_black_crows(data: pd.DataFrame) -> bool:
    """
    Checks for Three Black Crows pattern (strong bearish).
    - Three consecutive long bearish candles.
    - Each opens within the previous candle's body.
    - Each closes at a new low.
    """
    if len(data) < 3:
        return False
    c1, c2, c3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]

    # All three are bearish
    if not (c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] < c3['open']):
        return False

    # Each opens within the previous body
    opens_in_body = (c2['open'] < c1['open'] and c2['open'] > c1['close']) and \
                    (c3['open'] < c2['open'] and c3['open'] > c2['close'])

    # Each closes at a new low
    closes_lower = (c2['close'] < c1['close']) and (c3['close'] < c2['close'])

    # Optional: ensure they are not too short and don't have long lower wicks
    c1_body = c1['open'] - c1['close']
    c2_body = c2['open'] - c2['close']
    c3_body = c3['open'] - c3['close']
    no_long_wicks = (c1['close'] - c1['low']) < c1_body and \
                    (c2['close'] - c2['low']) < c2_body and \
                    (c3['close'] - c3['low']) < c3_body

    return opens_in_body and closes_lower and no_long_wicks

def get_candlestick_pattern(data: pd.DataFrame) -> str:
    """
    Identifies the most prominent recent candlestick pattern.
    Checks for patterns on the last one, two, or three candles.
    Priority is given to more complex (3-candle) patterns.
    """
    # Check 3-candle patterns first, as they are more significant
    if is_morning_star(data):
        return "Morning Star"
    if is_evening_star(data):
        return "Evening Star"
    if is_three_white_soldiers(data):
        return "Three White Soldiers"
    if is_three_black_crows(data):
        return "Three Black Crows"

    # Check 2-candle patterns
    if is_bullish_engulfing(data):
        return "Bullish Engulfing"
    if is_bearish_engulfing(data):
        return "Bearish Engulfing"

    # Check 1-candle patterns
    if is_hammer(data):
        return "Hammer"
    if is_doji(data):
        return "Doji"

    return "No Pattern"
