# Tests for FiboAnalyzer
import pandas as pd
import pytest
import numpy as np
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.data_retrieval.data_fetcher import DataFetcher
from unittest.mock import MagicMock

# A mock config for the analyzer
@pytest.fixture
def mock_config():
    return {
        'exchange': {
            'SANDBOX_MODE': True,
            'API_KEY': 'test',
            'API_SECRET': 'test',
            'PASSWORD': 'test'
        },
        'strategy_params': {
            'fibo_strategy': {
                'sma_period_fast': 10,
                'sma_period_slow': 30,
                'rsi_period': 14,
                'stoch_window': 14,
                'adx_window': 14,
                'atr_window': 14,
                'atr_multiplier': 2.0,
                'fib_lookback': 50
            }
        }
    }

# A mock data fetcher
@pytest.fixture
def mock_fetcher(mock_config):
    return DataFetcher(mock_config)

# Sample data for testing
@pytest.fixture
def sample_market_data():
    """
    Generates a DataFrame with 200 periods of realistic OHLC data to ensure
    it passes the post-indicator-calculation length check.
    """
    periods = 200
    # Start with a baseline close price
    close_prices = pd.Series([70.0] * periods, dtype=float)

    # 1. Old absolute low (will be ignored)
    close_prices.iloc[10] = 10.0

    # 2. RECENT SWING HIGH (the one we want to find) - adjusted index
    close_prices.iloc[160] = 95.0

    # 3. RECENT SWING LOW (the one we want to find) - adjusted index
    close_prices.iloc[180] = 50.0

    # 4. Absolute high at the end, but as part of an uptrend (so, not a peak) - adjusted index
    close_prices.iloc[195:] = np.linspace(140, 150, 5)

    # Create realistic OHLC data from the close prices
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=periods)),
        'open': close_prices - 1,
        'high': close_prices + 2,
        'low': close_prices - 2,
        'close': close_prices,
        'volume': [1000] * periods
    }

    # Explicitly set the exact high/low for our points of interest - adjusted index
    data['high'].iloc[160] = 95.0 # This is the peak
    data['low'].iloc[180] = 50.0  # This is the valley

    df = pd.DataFrame(data)
    for col in ['high', 'low', 'close', 'open', 'volume']:
        df[col] = pd.to_numeric(df[col])
    return df


def test_identifies_correct_recent_swing_points(mock_config, mock_fetcher, sample_market_data):
    """
    This test asserts the correct behavior: the analyzer should find the most
    recent significant swing points, not the absolute max/min of the dataset.
    """
    # Arrange
    analyzer = FiboAnalyzer(mock_config, mock_fetcher)
    # These are the *correct* recent swing points from the new sample data
    correct_swing_high = 95.0
    correct_swing_low = 50.0

    # Act
    result = analyzer.get_analysis(sample_market_data, 'DUMMY-USDT', '1D')

    # Assert
    assert result is not None
    assert 'swing_high' in result
    assert 'swing_low' in result
    assert result['swing_high']['price'] == correct_swing_high
    assert result['swing_low']['price'] == correct_swing_low