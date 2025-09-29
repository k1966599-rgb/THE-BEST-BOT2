import pytest
import pandas as pd
from src.utils.chart_generator import generate_analysis_chart

@pytest.fixture
def sample_ohlcv_data():
    """Creates a sample DataFrame with OHLCV data for testing."""
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=100, freq='H')),
        'open': [100 + i for i in range(100)],
        'high': [105 + i for i in range(100)],
        'low': [98 + i for i in range(100)],
        'close': [102 + i for i in range(100)],
        'volume': [1000 + i * 10 for i in range(100)],
        'sma_fast': [101 + i for i in range(100)],
        'sma_slow': [100 + i for i in range(100)],
    }
    df = pd.DataFrame(data)
    # Convert timestamp to milliseconds since epoch, as expected by the chart generator
    df['timestamp'] = df['timestamp'].astype('int64') // 10**6
    return df

@pytest.fixture
def sample_analysis_data():
    """Creates a sample analysis data dictionary."""
    return {
        'timeframe': '1H',
        'swing_high': {'price': 195},
        'swing_low': {'price': 110},
        'retracements': {
            'fib_382': 160,
            'fib_500': 152.5,
            'fib_618': 145,
        }
    }

def test_generate_analysis_chart_returns_bytes(sample_ohlcv_data, sample_analysis_data):
    """
    Tests that generate_analysis_chart returns a non-empty bytes object
    which is a valid PNG image.
    """
    # Arrange
    symbol = "BTC-USDT"

    # Act
    chart_bytes = generate_analysis_chart(sample_ohlcv_data, sample_analysis_data, symbol)

    # Assert
    assert isinstance(chart_bytes, bytes), "The function should return a bytes object."
    assert len(chart_bytes) > 0, "The returned bytes object should not be empty."

    # Check for PNG file signature (89 50 4E 47 0D 0A 1A 0A)
    # This confirms it's a PNG image file.
    png_signature = b'\x89PNG\r\n\x1a\n'
    assert chart_bytes.startswith(png_signature), "The returned bytes should be a valid PNG image."

def test_generate_analysis_chart_handles_error_gracefully():
    """
    Tests that the function returns an empty bytes object when input data is invalid.
    """
    # Arrange: Create an empty DataFrame which will cause an error inside the function
    invalid_df = pd.DataFrame()
    analysis_data = {}
    symbol = "ERROR-USDT"

    # Act
    chart_bytes = generate_analysis_chart(invalid_df, analysis_data, symbol)

    # Assert
    assert isinstance(chart_bytes, bytes), "The function should return a bytes object on error."
    assert len(chart_bytes) == 0, "The function should return an empty bytes object on error."