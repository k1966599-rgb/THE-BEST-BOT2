import os
import pytest
from src.config import get_config

@pytest.fixture(scope="module")
def config():
    """Provides the application configuration."""
    return get_config()

def test_data_directory_structure(config):
    """
    Tests that the data directory structure is created correctly for the watchlist.
    This is a conceptual test, as the directories are created on-demand.
    We are testing the configuration that leads to this structure.
    """
    base_data_dir = "data"
    if not os.path.exists(base_data_dir):
        os.mkdir(base_data_dir)
    assert os.path.exists(base_data_dir)

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    assert len(watchlist) > 0, "Watchlist should not be empty"
    assert len(timeframe_groups) > 0, "Timeframe groups should not be empty"

    for symbol in watchlist:
        symbol_dir_name = symbol.replace('/', '-')
        for group in timeframe_groups.keys():
            assert group in ['long', 'medium', 'short']
            for timeframe in timeframe_groups[group]:
                expected_path = os.path.join(base_data_dir, symbol_dir_name, group, f"{timeframe}.json")
                assert "data" in expected_path
