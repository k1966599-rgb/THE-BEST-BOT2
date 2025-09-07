import pandas as pd
import pytest
import sys
import os

# Add the root directory to the Python path to allow for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis.divergence import detect_divergence

@pytest.fixture
def sample_data_bullish_divergence():
    """
    Creates a DataFrame with a clear bullish divergence.
    Price makes a lower low, while RSI makes a higher low.
    """
    price = [10, 8, 9, 7, 10, 11, 12]
    rsi =   [40, 25, 35, 30, 60, 70, 75]
    return pd.Series(price, name="Close"), pd.Series(rsi, name="RSI_14")

@pytest.fixture
def sample_data_bearish_divergence():
    """
    Creates a DataFrame with a clear bearish divergence.
    Price makes a higher high, while RSI makes a lower high.
    The RSI data is crafted to ensure two clear peaks are present.
    """
    price = [50, 55, 52, 58, 54, 53, 50] # Higher Highs at 55 and 58
    rsi =   [70, 80, 75, 79, 70, 65, 60] # Lower Highs at 80 and 79
    return pd.Series(price, name="Close"), pd.Series(rsi, name="RSI_14")

@pytest.fixture
def sample_data_no_divergence():
    """
    Creates a DataFrame with no divergence.
    """
    price = [20, 25, 22, 30, 28, 35, 33]
    rsi =   [50, 60, 55, 70, 65, 80, 75]
    return pd.Series(price, name="Close"), pd.Series(rsi, name="RSI_14")

def test_bullish_divergence_detection(sample_data_bullish_divergence):
    """
    Tests if the function correctly identifies bullish divergence.
    """
    price_series, rsi_series = sample_data_bullish_divergence
    divergences = detect_divergence(price_series, rsi_series, distance=1)

    assert len(divergences) > 0, "Should find at least one divergence"
    assert divergences[0]['type'] == 'Bullish'

def test_bearish_divergence_detection(sample_data_bearish_divergence):
    """
    Tests if the function correctly identifies bearish divergence.
    """
    price_series, rsi_series = sample_data_bearish_divergence
    divergences = detect_divergence(price_series, rsi_series, distance=1)

    assert len(divergences) > 0, "Should find at least one divergence"
    assert divergences[0]['type'] == 'Bearish'

def test_no_divergence(sample_data_no_divergence):
    """
    Tests that the function does not find divergence when there is none.
    """
    price_series, rsi_series = sample_data_no_divergence
    divergences = detect_divergence(price_series, rsi_series, distance=1)

    assert len(divergences) == 0, "Should find no divergences"

# --- Tests for MACD Divergence ---

@pytest.fixture
def sample_data_macd_bullish_divergence():
    """
    Creates a DataFrame with a clear bullish MACD divergence.
    Price makes a lower low, while MACD histogram makes a higher low.
    """
    price = [100, 95, 98, 92, 96, 100, 105] # Lower low: 95 -> 92
    macd_hist = [-1.0, -2.5, -0.5, -1.5, 0.5, 1.0, 1.5] # Higher low: -2.5 -> -1.5
    return pd.Series(price, name="Close"), pd.Series(macd_hist, name="MACDh_12_26_9")

@pytest.fixture
def sample_data_macd_bearish_divergence():
    """
    Creates a DataFrame with a clear bearish MACD divergence.
    Price makes a higher high, while MACD histogram makes a lower high.
    """
    price = [100, 105, 102, 108, 104, 103, 100] # Higher high: 105 -> 108
    macd_hist = [1.0, 2.5, 0.5, 1.5, -0.5, -1.0, -1.5] # Lower high: 2.5 -> 1.5
    return pd.Series(price, name="Close"), pd.Series(macd_hist, name="MACDh_12_26_9")

def test_macd_bullish_divergence_detection(sample_data_macd_bullish_divergence):
    """
    Tests if the function correctly identifies bullish MACD divergence.
    """
    price_series, macd_series = sample_data_macd_bullish_divergence
    divergences = detect_divergence(price_series, macd_series, distance=1)

    assert len(divergences) > 0, "Should find MACD bullish divergence"
    assert divergences[0]['type'] == 'Bullish'

def test_macd_bearish_divergence_detection(sample_data_macd_bearish_divergence):
    """
    Tests if the function correctly identifies bearish MACD divergence.
    """
    price_series, macd_series = sample_data_macd_bearish_divergence
    divergences = detect_divergence(price_series, macd_series, distance=1)

    assert len(divergences) > 0, "Should find MACD bearish divergence"
    assert divergences[0]['type'] == 'Bearish'
