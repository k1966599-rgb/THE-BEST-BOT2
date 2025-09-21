import pandas as pd
import numpy as np
import pytest

from src.utils.indicators import find_swing_points, detect_divergence

def test_divergence_is_detected_after_fix():
    """
    This test verifies that the divergence detection bug is fixed.
    It creates a scenario with a clear bearish divergence and asserts that
    the fixed function correctly detects it.
    """
    # 1. Create a robust dataset with bearish divergence
    data_len = 200
    price_data = np.linspace(100, 150, data_len)
    rsi_data = np.linspace(40, 80, data_len)

    # Create the first price peak and a corresponding high RSI peak
    price_data[150] = 160
    rsi_data[150] = 85 # RSI Peak 1

    # Create a higher peak in price, but a lower peak in RSI (the divergence)
    price_data[180] = 165 # Higher High in price
    rsi_data[180] = 80  # Lower High in RSI

    df = pd.DataFrame({
        'high': price_data,
        'low': price_data - 5,
        'close': price_data - 2,
        'rsi': rsi_data,
        'volume': np.random.randint(100, 1000, data_len)
    })
    # Use a non-zero-based index to simulate real-world data
    df.index = range(100, 100 + data_len)

    # 2. Find swing points
    swings = find_swing_points(df, lookback=100, prominence_multiplier=0.1)

    # Sanity check that our peaks are found
    assert len(swings['highs']) >= 2

    # 3. Detect divergence
    is_divergence_present = detect_divergence(swings['highs'], df['rsi'], 'bearish')

    # 4. Assert the fix is working
    # The fixed function should now correctly identify the divergence.
    assert is_divergence_present is True, "The bug is not fixed. The function still fails to detect the divergence."
