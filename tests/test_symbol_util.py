import pytest
from src.utils.symbol_util import normalize_symbol

@pytest.mark.parametrize("input_symbol, expected_output", [
    ("BTC/USDT", "BTC-USDT"),
    ("ETH-USDT", "ETH-USDT"),
    ("sol/usdt", "SOL-USDT"),
    ("LINK-usd", "LINK-USD"),
    ("DOGE", "DOGE"),
    ("btc", "BTC"),
    ("", ""),
    (None, ""),
    ("BTC-USDT-SWAP", "BTC-USDT-SWAP"),
])
def test_normalize_symbol(input_symbol, expected_output):
    """
    Tests the central symbol normalization function with various inputs.
    """
    assert normalize_symbol(input_symbol) == expected_output