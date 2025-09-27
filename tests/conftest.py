import pytest
import pandas as pd
from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher

@pytest.fixture(scope="session")
def mock_config():
    """
    Provides a default configuration for tests.
    """
    return get_config()

@pytest.fixture(scope="session")
def mock_fetcher(mock_config):
    """
    Provides a mock DataFetcher instance.
    In a real-world scenario, you might want to patch its methods
    to avoid actual network calls.
    """
    return DataFetcher(mock_config)

@pytest.fixture
def sample_candlestick_data():
    """
    Provides a sample DataFrame of candlestick data for testing.
    This data can be modified within tests to simulate different scenarios.
    """
    # Creates 300 rows of sample data
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=300, freq='H')),
        'open': [100 + i for i in range(300)],
        'high': [105 + i for i in range(300)],
        'low': [98 + i for i in range(300)],
        'close': [102 + i for i in range(300)],
        'volume': [1000 + (i * 10) for i in range(300)],
        'volCcy': ['USDT'] * 300,
        'volCcyQuote': ['USDT'] * 300,
        'confirm': [1] * 300,
    }
    df = pd.DataFrame(data)
    df['timestamp'] = df['timestamp'].apply(lambda x: int(x.timestamp() * 1000))
    return df