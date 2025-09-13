import pytest
from src.data.okx_fetcher import OKXDataFetcher
from src.config import get_config

@pytest.fixture
def fetcher():
    """Returns an instance of OKXDataFetcher."""
    config = get_config()
    return OKXDataFetcher(config)

@pytest.mark.parametrize("timeframe, expected_minutes", [
    ('5m', 5),
    ('15m', 15),
    ('30m', 30),
    ('1h', 60),
    ('4h', 240),
    ('1d', 1440),
    ('1H', 60),
    ('4H', 240),
    ('1D', 1440),
    ('2h', 120),
    ('2H', 120),
    ('3m', 3)
])
def test_timeframe_to_minutes(fetcher, timeframe, expected_minutes):
    """
    Tests the _timeframe_to_minutes method with various timeframes.
    This test will fail for lowercase 'h' and 'd' timeframes before the fix.
    """
    assert fetcher._timeframe_to_minutes(timeframe) == expected_minutes
