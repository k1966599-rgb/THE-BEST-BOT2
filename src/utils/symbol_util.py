def normalize_symbol(symbol: str) -> str:
    """
    Centralized function to normalize a trading symbol.

    This ensures that symbols are handled consistently across the application,
    whether for API calls or for creating file paths.

    - Replaces '/' with '-'
    - Converts to uppercase

    Args:
        symbol (str): The input symbol (e.g., 'BTC/USDT' or 'btc-usdt').

    Returns:
        str: The normalized symbol (e.g., 'BTC-USDT').
    """
    if not isinstance(symbol, str):
        return ""
    return symbol.replace('/', '-').upper()