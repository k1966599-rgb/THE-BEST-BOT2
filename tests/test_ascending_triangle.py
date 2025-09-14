import pytest
import pandas as pd
from src.analysis.patterns.ascending_triangle import AscendingTriangle
from src.config import get_config

@pytest.fixture
def sample_data_for_triangle():
    """Provides sample DataFrame for testing triangle patterns."""
    data = {
        'high': [105, 102, 105.1, 103, 105.2, 104, 108],
        'low':  [100, 101, 101.5, 102, 102.5, 103, 106],
        'close':[102, 101.5, 104.8, 102.5, 104.9, 103.5, 107],
        'open': [101, 101.5, 102, 102.5, 103, 103.5, 105]
    }
    df = pd.DataFrame(data)
    # Ensure the dataframe has a DatetimeIndex, as expected by some utility functions
    df.index = pd.to_datetime(pd.date_range(start='2023-01-01', periods=len(df)))
    return df

def test_ascending_triangle_detection(sample_data_for_triangle):
    """
    Tests the improved Ascending Triangle detection logic.
    """
    config = get_config()
    # Mock pivots to be predictable for the test
    highs = [{'price': 105, 'index': 0}, {'price': 105.1, 'index': 2}, {'price': 105.2, 'index': 4}]
    lows = [{'price': 100, 'index': 0}, {'price': 101, 'index': 1}, {'price': 101.5, 'index': 2}]

    current_price = sample_data_for_triangle['close'].iloc[-1]
    price_tolerance = config.get('analysis', {}).get('PATTERN_PRICE_TOLERANCE', 0.03)

    triangle_detector = AscendingTriangle(
        df=sample_data_for_triangle,
        config=config.get('analysis', {}),
        highs=highs,
        lows=lows,
        current_price=current_price,
        price_tolerance=price_tolerance,
        timeframe='1h'
    )

    patterns = triangle_detector.check()

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.name == "المثلث الصاعد"
    # The resistance should be the mean of the clustered highs
    assert pattern.activation_level == pytest.approx(105.1)
