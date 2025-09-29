import pytest
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.telegram_bot import _fetch_and_prepare_data

@pytest.mark.anyio
async def test_btc_1d_analysis_runs_successfully(mock_config, mock_fetcher):
    """
    This test now verifies that the analysis for BTC-USDT on the 1D timeframe
    completes successfully without raising an InsufficientDataError,
    proving that the underlying bug has been fixed.
    """
    symbol = "BTC-USDT"
    timeframe = "1D"

    # The analyzer's default settings are now expected to work correctly
    # with the data fetched from the exchange for the 1D timeframe.
    analyzer = FiboAnalyzer(mock_config, mock_fetcher, timeframe=timeframe)

    # Fetch the data
    df = await _fetch_and_prepare_data(mock_fetcher, symbol, timeframe, limit=300)

    # We now expect the analysis to complete without any errors.
    analysis_result = analyzer.get_analysis(df, symbol, timeframe)

    # Assert that the analysis returned a valid result dictionary.
    assert analysis_result is not None, "Analysis result should not be None."
    assert "signal" in analysis_result, "Analysis result should contain a 'signal' key."
    assert "trend" in analysis_result, "Analysis result should contain a 'trend' key."
    print(f"\nSUCCESS: Test passed, analysis for {symbol} {timeframe} completed without errors.")