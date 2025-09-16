import pandas as pd
import numpy as np
from src.utils.indicators import calculate_bollinger_bands, calculate_atr

def sample_data():
    """Generates a sample DataFrame for testing."""
    return pd.DataFrame({
        'high': np.array([110, 112, 115, 112, 108, 110, 114, 116, 118, 120]),
        'low': np.array([100, 102, 105, 103, 100, 102, 105, 107, 109, 110]),
        'close': np.array([105, 107, 110, 108, 105, 107, 110, 112, 115, 118])
    })

def test_calculate_bollinger_bands():
    """Tests the Bollinger Bands calculation."""
    data = sample_data()
    window = 5
    bb_df = calculate_bollinger_bands(data, window=window)

    assert 'upper_band' in bb_df.columns
    assert 'middle_band' in bb_df.columns
    assert 'lower_band' in bb_df.columns
    # The first (window - 1) values will be NaN, which is expected.
    assert not bb_df.iloc[window-1:].isnull().sum().any()

def test_calculate_atr():
    """Tests the ATR calculation."""
    data = sample_data()
    atr = calculate_atr(data, window=5)

    assert isinstance(atr, pd.Series)
    assert not atr.isnull().any()
