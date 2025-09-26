import pytest
import pandas as pd
import numpy as np
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.config import get_config

@pytest.fixture
def sample_data():
    """
    Provides a sample DataFrame for testing, long enough for all indicator calculations.
    Using 250 periods to be safe for indicators like a 200-period SMA.
    """
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=250)),
        'high': [100 + i + (1 if i % 10 == 0 else 0) for i in range(250)],
        'low': [90 + i - (1 if i % 10 == 0 else 0) for i in range(250)],
        'close': [95 + i for i in range(250)],
        'open': [92 + i for i in range(250)],
        'volume': [1000 for _ in range(250)]
    }
    df = pd.DataFrame(data)
    return df

@pytest.fixture
def analyzer():
    """Provides an instance of FiboAnalyzer."""
    config = get_config()
    # We pass None for the fetcher as it's not used in these unit tests.
    return FiboAnalyzer(config, fetcher=None)

def test_get_analysis_returns_valid_structure(analyzer, sample_data):
    """
    Tests that the main get_analysis method returns a dictionary with the
    expected structure and that key values have the correct types.
    """
    symbol = "BTC-USDT"
    timeframe = "1H"

    # The get_analysis method expects the DataFrame passed to it.
    analysis = analyzer.get_analysis(sample_data, symbol, timeframe)

    assert isinstance(analysis, dict)

    # Check for the actual keys returned by the method based on fibo_analyzer.py
    expected_keys = [
        'trend', 'signal', 'reason', 'score', 'swing_high', 'swing_low',
        'retracements', 'extensions', 'confluence_zones', 'pattern',
        'risk_levels', 'scenarios', 'latest_data', 'current_price'
    ]
    for key in expected_keys:
        assert key in analysis, f"Expected key '{key}' not found in analysis result."

    # Check a few key types and basic validity
    assert isinstance(analysis['current_price'], (float, int, np.number))
    # Note: The trend from moving averages can be different from the Fibo trend.
    # The result returns the main trend.
    assert analysis['trend'] in ['up', 'down', 'N/A']
    assert analysis['signal'] in ['BUY', 'SELL', 'HOLD']
    assert isinstance(analysis['score'], int)
    assert isinstance(analysis['retracements'], dict)
    assert isinstance(analysis['extensions'], dict)
    assert isinstance(analysis['scenarios'], dict)

    # If the analysis was successful, swings should be populated correctly.
    if not analysis.get('reason'):
        assert isinstance(analysis['swing_high'], dict)
        assert 'price' in analysis['swing_high']
        assert isinstance(analysis['swing_low'], dict)
        assert 'price' in analysis['swing_low']