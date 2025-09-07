import pytest
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from indicators import apply_all_indicators

@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing indicator calculations."""
    data = {
        'High': np.random.uniform(100, 110, size=250),
        'Low': np.random.uniform(90, 100, size=250),
        'Open': np.random.uniform(95, 105, size=250),
        'Close': np.random.uniform(98, 108, size=250),
        'Volume': np.random.uniform(1000, 5000, size=250)
    }
    df = pd.DataFrame(data)
    df['Low'] = df[['High', 'Low']].min(axis=1)
    return df

def test_apply_all_indicators(sample_dataframe):
    """
    Test that the apply_all_indicators function runs without errors and
    adds the expected indicator columns to the DataFrame.
    """
    df = sample_dataframe
    df_with_indicators = apply_all_indicators(df)

    assert isinstance(df_with_indicators, pd.DataFrame)

    # Updated column names based on the new pandas_ta version
    expected_columns = [
        'SMA_20', 'SMA_50', 'SMA_200',
        'EMA_20', 'EMA_50', 'EMA_100',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'BBL_20_2.0_2.0', 'BBM_20_2.0_2.0', 'BBU_20_2.0_2.0', # Corrected names
        'STOCHk_14_3_3', 'STOCHd_14_3_3',
        'ATRr_14',
        'OBV',
        'ADX_14'
    ]

    for col in expected_columns:
        assert col in df_with_indicators.columns, f"Column '{col}' is missing from DataFrame after applying indicators."

    for col in expected_columns:
        assert pd.api.types.is_numeric_dtype(df_with_indicators[col]), f"Column '{col}' is not numeric."
        assert not df_with_indicators[col].iloc[-50:].isnull().all(), f"Column '{col}' is all NaNs in the last 50 periods."
