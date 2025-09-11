import json
import os
import pytest

# List of historical data files that should exist
# This can be dynamically generated from the config if needed
EXPECTED_FILES = [
    "BTC-USDT_historical.json",
    "ETH-USDT_historical.json",
    "SOL-USDT_historical.json",
    "LINK-USDT_historical.json",
    "DOGE-USDT_historical.json"
]

@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_historical_data_file_exists(filename):
    """Tests that the historical data files exist."""
    assert os.path.exists(filename), f"Historical data file not found: {filename}"

@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_historical_data_format(filename):
    """
    Tests that the historical data files are in the correct dictionary format.
    """
    with open(filename, 'r') as f:
        data = json.load(f)

    # 1. Check if the root object is a dictionary
    assert isinstance(data, dict), f"File {filename} is not a dictionary."

    # 2. Check for the required keys
    required_keys = ['symbol', 'last_update', 'data']
    for key in required_keys:
        assert key in data, f"Key '{key}' not found in {filename}."

    # 3. Check the type of the 'data' key
    assert isinstance(data['data'], list), f"'data' key in {filename} is not a list."

    # 4. Check the structure of the first candle in the list (if it exists)
    if data['data']:
        first_candle = data['data'][0]
        assert isinstance(first_candle, dict), f"Candle in {filename} is not a dictionary."
        candle_keys = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'date']
        for key in candle_keys:
            assert key in first_candle, f"Candle key '{key}' not found in {filename}."
