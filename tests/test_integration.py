import pytest
import pandas as pd
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.strategies.exceptions import InsufficientDataError
from src.telegram_bot import _fetch_and_prepare_data

def test_btc_1d_analysis_raises_error_on_clean_code(mock_config, mock_fetcher):
    """
    This test is designed to FAIL on the clean codebase by raising
    an InsufficientDataError, proving that the bug exists.
    After the fix is applied, this test should PASS.
    """
    symbol = "BTC-USDT"
    timeframe = "1D"

    # On the clean, un-fixed code, the analyzer's default settings
    # will require more data than OKX provides for the 1D timeframe.
    analyzer = FiboAnalyzer(mock_config, mock_fetcher, timeframe=timeframe)

    # We expect this to fail by raising InsufficientDataError
    with pytest.raises(InsufficientDataError) as excinfo:
        # We fetch a large number of candles, but the analyzer will fail
        # because its internal requirements (SMA 200) are too high for the data.
        df = _fetch_and_prepare_data(mock_fetcher, symbol, timeframe, limit=300)
        analyzer.get_analysis(df, symbol, timeframe)

    # Assert that the correct exception was raised.
    # This proves the bug is reproducible.
    assert "Not enough data for swing analysis" in str(excinfo.value)
    print(f"\nSUCCESS: Test correctly failed as expected with InsufficientDataError: {excinfo.value}")