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
    """
    Checks if a given symbol/timeframe combination is likely supported for OKX.
    Raises ValueError if not found in the supported list.
    The symbol format is 'BTC/USDT'.
    """
    okx_symbol = symbol.replace('/', '-')
    supported_for_symbol = SUPPORTED_COMBINATIONS.get(okx_symbol)

    # If the symbol is not explicitly listed, assume it has the same support as ETH (more comprehensive).
    if not supported_for_symbol:
        supported_for_symbol = SUPPORTED_COMBINATIONS['ETH-USDT']

    if timeframe not in supported_for_symbol:
        raise ValueError(f"Timeframe {timeframe} is not supported for {symbol} on OKX.")
