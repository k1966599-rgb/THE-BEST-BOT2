import pandas as pd
import numpy as np
import pytest
from src.utils.indicators import detect_divergence

def test_bullish_divergence_detection():
    """Tests that bullish divergence is correctly identified."""
    price_swings = [
        {'price': 100, 'index': 10},
        {'price': 95, 'index': 20} # Lower low in price
    ]
    # Create a Series where the index matches the original dataframe's index
    indicator_series = pd.Series(np.nan, index=range(30))
    indicator_series.iloc[10] = 30
    indicator_series.iloc[20] = 35 # Higher low in indicator

    assert detect_divergence(price_swings, indicator_series, 'bullish') == True

def test_no_bullish_divergence():
    """Tests that bullish divergence is not found when conditions aren't met."""
    price_swings = [
        {'price': 100, 'index': 10},
        {'price': 95, 'index': 20} # Lower low in price
    ]
    indicator_series = pd.Series(np.nan, index=range(30))
    indicator_series.iloc[10] = 30
    indicator_series.iloc[20] = 25 # Lower low in indicator as well

    assert detect_divergence(price_swings, indicator_series, 'bullish') == False

def test_bearish_divergence_detection():
    """Tests that bearish divergence is correctly identified."""
    price_swings = [
        {'price': 100, 'index': 10},
        {'price': 105, 'index': 20} # Higher high in price
    ]
    indicator_series = pd.Series(np.nan, index=range(30))
    indicator_series.iloc[10] = 70
    indicator_series.iloc[20] = 65 # Lower high in indicator

    assert detect_divergence(price_swings, indicator_series, 'bearish') == True
