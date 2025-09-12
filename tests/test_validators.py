import pytest
from src.utils.validators import validate_symbol_timeframe, SUPPORTED_COMBINATIONS

def test_validate_symbol_timeframe_supported():
    """
    Tests that the function passes for a supported symbol and timeframe.
    """
    # Using a known supported combination
    symbol = 'BTC/USDT'
    timeframe = '1h'
    # This should not raise any exception
    validate_symbol_timeframe(symbol, timeframe)

def test_validate_symbol_timeframe_unsupported_timeframe():
    """
    Tests that the function raises a ValueError for an unsupported timeframe
    for a supported symbol.
    """
    symbol = 'BTC/USDT'
    timeframe = '1y' # Assuming '1y' is not a supported timeframe
    with pytest.raises(ValueError, match=f"Timeframe {timeframe} is not supported for {symbol}"):
        validate_symbol_timeframe(symbol, timeframe)

def test_validate_symbol_timeframe_unsupported_symbol():
    """
    This is the test case that should fail with the current implementation
    and pass after the fix.
    It tests that the function raises a ValueError for an unsupported symbol.
    """
    unsupported_symbol = 'SHIB/USDT'
    timeframe = '1h'
    with pytest.raises(ValueError, match=f"Symbol {unsupported_symbol} is not supported."):
        validate_symbol_timeframe(unsupported_symbol, timeframe)

def test_validate_symbol_timeframe_defaults_to_eth_for_unknown_symbol_bug():
    """
    This test explicitly checks for the bug: an unknown symbol should not default
    to ETH's supported timeframes. It should fail if a ValueError is raised,
    which is the desired behavior after the fix.
    """
    # This symbol is not in SUPPORTED_COMBINATIONS
    unknown_symbol = "XYZ/USDT"
    # This timeframe is supported for ETH, so without the fix, this test would pass.
    timeframe_supported_by_eth = "5m"

    # The buggy behavior is that this does NOT raise an error.
    # After the fix, it SHOULD raise a ValueError.
    with pytest.raises(ValueError, match=f"Symbol {unknown_symbol} is not supported."):
        validate_symbol_timeframe(unknown_symbol, timeframe_supported_by_eth)

def test_validate_symbol_timeframe_supported_uppercase():
    """
    Tests that the function passes for a supported symbol and an uppercase timeframe.
    This test will fail before the fix is applied.
    """
    symbol = 'BTC/USDT'
    timeframe = '1H'
    # This should not raise any exception after the fix
    validate_symbol_timeframe(symbol, timeframe)
