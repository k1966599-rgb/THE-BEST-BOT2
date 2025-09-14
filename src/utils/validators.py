# This file contains functions for validating data and parameters.

# Based on the analysis of logs, some timeframes are not supported for all pairs on OKX.
# This list can be expanded or fetched dynamically in a future improvement.
SUPPORTED_COMBINATIONS = {
    'BTC-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'ETH-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'SOL-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'XRP-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'DOGE-USDT':  ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'ADA-USDT':   ['1m', '3m', '1h', '2h', '4h', '1d'], # This one seems to have fewer supported timeframes
    'AVAX-USDT':  ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'DOT-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'BNB-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'MATIC-USDT': ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
}

def validate_symbol_timeframe(symbol: str, timeframe: str):
    """Checks if a given symbol/timeframe combination is supported by OKX.

    This function raises a ValueError if the symbol or timeframe is not in the
    list of supported combinations.

    Args:
        symbol (str): The trading symbol (e.g., 'BTC/USDT').
        timeframe (str): The timeframe (e.g., '15m').

    Raises:
        ValueError: If the symbol or timeframe is not supported.
    """
    okx_symbol = symbol.replace('/', '-').upper()
    if okx_symbol not in SUPPORTED_COMBINATIONS:
        raise ValueError(f"Symbol {symbol} is not supported.")

    supported_for_symbol = SUPPORTED_COMBINATIONS[okx_symbol]

    if timeframe.lower() not in supported_for_symbol:
        raise ValueError(f"Timeframe {timeframe} is not supported for {symbol} on OKX.")
