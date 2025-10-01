import os
import pytest
import time
from src.cache_manager import CacheManager
from src.database import DatabaseManager

# Use a temporary database for testing
TEST_DB_PATH = 'data/test_cache.db'

@pytest.fixture(scope="module")
def cache_manager():
    """
    Pytest fixture to set up and tear down a CacheManager with a test database.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)

    # Setup: create a new cache manager instance for the test module
    manager = CacheManager(db_path=TEST_DB_PATH, default_ttl_hours=1/3600) # 1 second TTL for testing
    yield manager

    # Teardown: close connection and remove the test database
    manager.db.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_set_and_get_fresh_data(cache_manager):
    """
    Tests that we can save data and immediately retrieve it.
    """
    symbol = "BTC/USDT"
    timeframe = "1h"
    test_data = [
        {'timestamp': 1672531200000, 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000}
    ]

    # Set data in cache
    cache_manager.set(symbol, timeframe, test_data)

    # Get data immediately
    retrieved_data = cache_manager.get(symbol, timeframe)

    assert retrieved_data is not None
    assert len(retrieved_data) == 1
    assert retrieved_data[0]['close'] == 105

def test_get_non_existent_data(cache_manager):
    """
    Tests that getting a non-existent symbol returns None.
    """
    retrieved_data = cache_manager.get("NON-EXISTENT", "1d")
    assert retrieved_data is None

def test_cache_expiration(cache_manager):
    """
    Tests that data expires after the TTL and get() returns None.
    """
    symbol = "ETH/USDT"
    timeframe = "4h"
    test_data = [
        {'timestamp': 1672531200000, 'open': 2000, 'high': 2100, 'low': 1900, 'close': 2050, 'volume': 5000}
    ]

    # Set data (CacheManager is initialized with a 1-second TTL)
    cache_manager.set(symbol, timeframe, test_data)

    # Wait for the cache to expire
    time.sleep(1.1)

    # Try to get the expired data
    retrieved_data = cache_manager.get(symbol, timeframe)

    assert retrieved_data is None

def test_set_empty_data_does_not_save(cache_manager):
    """
    Tests that calling set() with empty data does not create a cache entry.
    """
    symbol = "LTC/USDT"
    timeframe = "30m"

    # Attempt to set empty data
    cache_manager.set(symbol, timeframe, [])

    # Check that no data was saved
    retrieved_data = cache_manager.get(symbol, timeframe)
    assert retrieved_data is None

    # Also check the metadata directly
    metadata = cache_manager.db.get_cache_metadata(symbol, timeframe)
    assert metadata is None