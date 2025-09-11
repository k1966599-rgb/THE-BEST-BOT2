import pytest
from unittest.mock import MagicMock
from src.service_manager import ServiceManager
from src.data.okx_fetcher import OKXDataFetcher

@pytest.fixture
def mock_fetcher():
    """Fixture to create a mock OKXDataFetcher."""
    return MagicMock(spec=OKXDataFetcher)

def test_service_manager_start(mock_fetcher):
    """Test that start_services calls the fetcher's start_data_services."""
    service_manager = ServiceManager(mock_fetcher)
    symbols = ['BTC-USDT', 'ETH-USDT']

    service_manager.start_services(symbols)

    mock_fetcher.start_data_services.assert_called_once_with(symbols)

def test_service_manager_stop(mock_fetcher):
    """Test that stop_services calls the fetcher's stop method."""
    service_manager = ServiceManager(mock_fetcher)

    service_manager.stop_services()

    mock_fetcher.stop.assert_called_once()
