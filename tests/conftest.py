import pytest
import sys
import os
import pandas as pd
from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher

# Add the project root to the Python path to allow imports from 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def mock_config():
    """
    Provides a default configuration for tests.
    """
    return get_config()

@pytest.fixture(scope="session")
def mock_fetcher(mock_config):
    """
    Provides a real DataFetcher instance connected to the sandbox.
    This is for integration testing. For unit tests, we would mock this.
    """
    # Ensure sandbox mode is explicitly True for tests
    mock_config['exchange']['SANDBOX_MODE'] = True
    return DataFetcher(mock_config)