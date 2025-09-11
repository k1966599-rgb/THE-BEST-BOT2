import pytest
from unittest.mock import patch, MagicMock
from src.data.okx_fetcher import OKXDataFetcher
from src.config import get_config

@pytest.fixture
def config():
    """Fixture to provide a default config."""
    return get_config()

@pytest.fixture
def fetcher(config):
    """Fixture to create an OKXDataFetcher instance."""
    with patch('src.data.okx_fetcher.OKXWebSocketClient'):
        return OKXDataFetcher(config=config)

def test_fetcher_initialization(fetcher, config):
    """Test that the fetcher initializes correctly."""
    assert fetcher.config == config
    assert fetcher.default_symbols == config['trading']['DEFAULT_SYMBOLS']

def test_read_from_cache(fetcher):
    """Test reading from in-memory cache."""
    cache_key = ('BTC-USDT', '1D', 365)
    fetcher.historical_cache[cache_key] = {"data": "test_data"}

    result = fetcher._read_from_cache(cache_key)

    assert result == {"data": "test_data"}

@patch('src.data.okx_fetcher.Path.exists', return_value=True)
@patch('builtins.open')
@patch('json.load', return_value={"data": "file_data"})
def test_read_from_file_exists(mock_json_load, mock_open, mock_path_exists, fetcher):
    """Test reading from an existing file."""
    result = fetcher._read_from_file('BTC-USDT', '1D')

    assert result == {"data": "file_data"}
    mock_path_exists.assert_called_once()
    mock_open.assert_called_once()
    mock_json_load.assert_called_once()

@patch('src.data.okx_fetcher.Path.exists', return_value=False)
def test_read_from_file_not_exists(mock_path_exists, fetcher):
    """Test reading from a non-existent file."""
    result = fetcher._read_from_file('BTC-USDT', '1D')

    assert result is None

@patch('requests.get')
def test_fetch_from_network_success(mock_requests_get, fetcher):
    """Test successful fetching from network."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "0",
        "data": [["1622505600000", "36000", "37000", "35000", "36500", "1000", "2021-06-01T00:00:00Z"]]
    }
    mock_requests_get.return_value = mock_response

    result = fetcher._fetch_from_network('BTC-USDT', '1D', 1)

    assert len(result) == 1
    assert result[0][1] == "36000"

def test_process_candles(fetcher):
    """Test processing of raw candle data."""
    raw_candles = [["1622505600000", "36000", "37000", "35000", "36500", "1000", "2021-06-01T00:00:00Z"]]

    result = fetcher._process_candles(raw_candles, 'BTC-USDT')

    assert result['symbol'] == 'BTC/USDT'
    assert len(result['data']) == 1
    assert result['data'][0]['open'] == 36000

@patch.object(OKXDataFetcher, '_read_from_cache', return_value=None)
@patch.object(OKXDataFetcher, '_read_from_file', return_value=None)
@patch.object(OKXDataFetcher, '_fetch_from_network')
@patch.object(OKXDataFetcher, '_process_candles')
@patch.object(OKXDataFetcher, '_save_to_file')
def test_fetch_historical_data_orchestration(mock_save, mock_process, mock_fetch, mock_read_file, mock_read_cache, fetcher):
    """Test the main fetch_historical_data method's orchestration."""
    mock_fetch.return_value = ["raw_candle_data"]
    mock_process.return_value = {"data": ["processed_candle_data"]}

    fetcher.fetch_historical_data('BTC-USDT', '1D', 365)

    mock_read_cache.assert_called_once()
    mock_read_file.assert_called_once()
    mock_fetch.assert_called_once()
    mock_process.assert_called_once()
    mock_save.assert_called_once()
