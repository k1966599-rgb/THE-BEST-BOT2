import pandas as pd
import numpy as np
import pytest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from indicators import apply_all_indicators

@pytest.fixture
def sample_ohlcv_df():
    """Creates a sample DataFrame for testing."""
    np.random.seed(42)
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
    data = {
        'open': np.random.uniform(90, 110, 100).cumsum() + 1000,
        'high': np.random.uniform(0, 5, 100).cumsum() + 1005,
        'low': np.random.uniform(-5, 0, 100).cumsum() + 995,
        'close': np.random.uniform(-2, 2, 100).cumsum() + 1000,
        'volume': np.random.uniform(1000, 5000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    # Ensure high is always the highest and low is the lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df

def test_apply_all_indicators_adds_columns(sample_ohlcv_df):
    """
    Tests that apply_all_indicators function adds new columns to the DataFrame.
    """
    original_df = sample_ohlcv_df.copy()
    original_col_count = len(original_df.columns)

    # Apply indicators
    df_with_indicators = apply_all_indicators(original_df)

    # Assert that new columns have been added
    assert len(df_with_indicators.columns) > original_col_count

def test_apply_all_indicators_adds_specific_indicators(sample_ohlcv_df):
    """
    Tests that apply_all_indicators adds some well-known indicator columns.
    """
    df = sample_ohlcv_df.copy()

    # Apply indicators
    df_with_indicators = apply_all_indicators(df)

    # Check for a few specific indicators (column names are lowercased by our function)
    # The exact names depend on pandas_ta's strategy
    assert 'rsi_14' in df_with_indicators.columns
    assert 'macdh_12_26_9' in df_with_indicators.columns # Check for the histogram part of MACD
    assert 'bbands_20_2.0_bbl' in df_with_indicators.columns # Check for the lower Bollinger Band

def test_apply_all_indicators_handles_empty_df():
    """
    Tests that the function doesn't crash with an empty DataFrame.
    """
    empty_df = pd.DataFrame()
    result_df = apply_all_indicators(empty_df)
    assert result_df.empty
    assert len(result_df.columns) == 0
