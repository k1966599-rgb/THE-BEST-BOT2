import pytest
import pandas as pd
import os
import time
from unittest.mock import patch, MagicMock
from src.data_retrieval.data_fetcher import DataFetcher
from src.utils.exceptions import DataUnavailableError
from src.config import get_config

# Sample successful API response
SUCCESSFUL_API_RESPONSE = {
    "code": "0",
    "msg": "",
    "data": [
        ["1672617600000", "17000", "17100", "16900", "17050", "1000", "58.82", "1", "1"],
        ["1672531200000", "16500", "17000", "16400", "17000", "1200", "70.58", "1", "1"],
    ]
}

# Sample error API response
ERROR_API_RESPONSE = {"code": "51001", "msg": "Invalid instrument ID"}

@pytest.fixture
def temp_cache_config():
    """Fixture to create a temporary cache directory for testing."""
    config = get_config()
    # Override the cache directory for the test
    temp_dir = "tests/temp_cache"
    config['cache']['DIRECTORY'] = temp_dir
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    yield config

    # Teardown: clean up the cache files and directory
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)

@patch('okx.MarketData.MarketAPI')
def test_fetch_from_api_success(MockMarketAPI, temp_cache_config):
    """Tests a successful data fetch from the API and that it creates a cache file."""
    # Arrange
    mock_api_instance = MockMarketAPI.return_value
    mock_api_instance.get_history_candlesticks.return_value = SUCCESSFUL_API_RESPONSE

    fetcher = DataFetcher(temp_cache_config)

    # Act
    data = fetcher.fetch_historical_data("BTC-USDT", "1D", limit=2)

    # Assert
    mock_api_instance.get_history_candlesticks.assert_called_once()
    assert data is not None
    assert len(data['data']) == 2
    assert data['data'][0]['close'] == "17000" # Data is sorted ascending

    # Verify cache file was created
    cache_file = fetcher._get_cache_filepath("BTC-USDT", "1D", limit=2)
    assert os.path.exists(cache_file)

@patch('okx.MarketData.MarketAPI')
def test_fetch_uses_cache(MockMarketAPI, temp_cache_config):
    """Tests that a second call for the same data reads from cache instead of the API."""
    # Arrange
    mock_api_instance = MockMarketAPI.return_value
    mock_api_instance.get_history_candlesticks.return_value = SUCCESSFUL_API_RESPONSE

    fetcher = DataFetcher(temp_cache_config)

    # Act
    # First call - should hit the API and create cache
    fetcher.fetch_historical_data("ETH-USDT", "4H", limit=2)

    # Second call - should hit the cache
    fetcher.fetch_historical_data("ETH-USDT", "4H", limit=2)

    # Assert
    # The API should only have been called ONCE for the first fetch.
    mock_api_instance.get_history_candlesticks.assert_called_once()

@patch('okx.MarketData.MarketAPI')
def test_fetch_api_failure_raises_exception(MockMarketAPI, temp_cache_config):
    """Tests that an API error correctly raises a DataUnavailableError."""
    # Arrange
    mock_api_instance = MockMarketAPI.return_value
    mock_api_instance.get_history_candlesticks.return_value = ERROR_API_RESPONSE

    fetcher = DataFetcher(temp_cache_config)

    # Act & Assert
    with pytest.raises(DataUnavailableError):
        fetcher.fetch_historical_data("INVALID-SYMBOL", "1H", limit=10)

    # Verify no cache file was created on failure
    cache_file = fetcher._get_cache_filepath("INVALID-SYMBOL", "1H", limit=10)
    assert not os.path.exists(cache_file)