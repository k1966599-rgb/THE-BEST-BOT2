import pytest
import pandas as pd
from src.analysis.fibonacci import FibonacciAnalysis
from src.config import get_config

@pytest.fixture
def fib_analysis_instance():
    """Provides a FibonacciAnalysis instance with a test-friendly config."""
    config = get_config()['analysis']
    # Override the lookback for the '1h' timeframe specifically for this test
    config['TIMEFRAME_OVERRIDES']['1h']['FIB_LOOKBACK'] = 5
    return FibonacciAnalysis(config=config, timeframe='1h')

def test_fibonacci_uptrend_detection(fib_analysis_instance):
    """
    Tests that Fibonacci levels are calculated correctly based on an EMA-detected uptrend.
    """
    data = {
        'high': [100, 105, 110, 115, 120],
        'low': [95, 100, 105, 110, 115],
        'close': [98, 102, 108, 112, 118],
        'ema_20': [100, 101, 103, 106, 110],
        'ema_100': [90, 91, 92, 93, 94]
    }
    df = pd.DataFrame(data)

    result = fib_analysis_instance.analyze(df)

    support_levels = result['supports']
    assert any(level.name == "Fibonacci Support 0.5" and level.value == pytest.approx(107.5) for level in support_levels)

def test_fibonacci_downtrend_detection(fib_analysis_instance):
    """
    Tests that Fibonacci levels are calculated correctly based on an EMA-detected downtrend.
    """
    data = {
        'high': [120, 115, 110, 105, 100],
        'low': [115, 110, 105, 100, 95],
        'close': [118, 112, 108, 102, 98],
        'ema_20': [110, 108, 106, 104, 102],
        'ema_100': [120, 119, 118, 117, 116]
    }
    df = pd.DataFrame(data)

    result = fib_analysis_instance.analyze(df)

    resistance_levels = result['resistances']
    assert any(level.name == "Fibonacci Resistance 0.5" and level.value == pytest.approx(107.5) for level in resistance_levels)
