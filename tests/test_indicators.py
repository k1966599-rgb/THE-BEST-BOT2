import pandas as pd
import pytest
from src.utils.indicators import calculate_sma, calculate_rsi, calculate_macd

@pytest.fixture
def sample_data():
    """Pytest fixture to create sample data for testing."""
    data = {
        'open': [10, 11, 12, 13, 14, 15, 16],
        'high': [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5],
        'low': [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5],
        'close': [11, 12, 13, 14, 15, 14, 13],
        'volume': [100, 110, 120, 130, 140, 150, 160]
    }
    return pd.DataFrame(data)

def test_calculate_sma(sample_data):
    """
    Tests the Simple Moving Average calculation.
    """
    sma = calculate_sma(sample_data, window=3)
    assert sma.iloc[-1] == pytest.approx((15 + 14 + 13) / 3)
    assert pd.isna(sma.iloc[0])
    assert pd.isna(sma.iloc[1])

def test_calculate_rsi(sample_data):
    """
    Tests the Relative Strength Index calculation.
    This is a basic test to ensure it runs and produces a value.
    Validating the exact RSI value is complex, so we check for range and type.
    """
    # RSI needs more data points to be stable
    data = pd.concat([sample_data] * 5, ignore_index=True)
    rsi = calculate_rsi(data, window=14)
    assert isinstance(rsi, pd.Series)
    # RSI values must be between 0 and 100
    assert (rsi.dropna() >= 0).all() and (rsi.dropna() <= 100).all()
    # The last value should be a number
    assert not pd.isna(rsi.iloc[-1])

def test_calculate_macd(sample_data):
    """
    Tests the MACD calculation.
    """
    macd_df = calculate_macd(sample_data, fast_period=3, slow_period=5, signal_period=3)
    assert isinstance(macd_df, pd.DataFrame)
    assert 'macd' in macd_df.columns
    assert 'signal_line' in macd_df.columns
    assert 'histogram' in macd_df.columns
    assert not pd.isna(macd_df['macd'].iloc[-1])
