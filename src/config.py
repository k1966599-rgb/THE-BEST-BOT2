"""
Configuration settings for the trading bot.
"""
import os
from dotenv import load_dotenv

# It's good practice to load environment variables at the start.
# This will load the .env file at the project root.
load_dotenv()

# --- Trading Parameters ---
TRADING_CONFIG = {
    'WATCHLIST': [
        'BTC-USDT',
        'ETH-USDT',
        'SOL-USDT',
        'LINK-USDT',
        'DOGE-USDT'
    ],
    # All timeframes required for analysis
    'TIMEFRAMES': ['1D', '4H', '1H', '30m', '15m', '5m', '3m'],

    # Grouping for different analysis types, can be used later
    'TIMEFRAME_GROUPS': {
        "long_term": ['1D', '4H', '1H'],
        "medium_term": ['30m', '15m'],
        "short_term": ['5m', '3m']
    }
}

# --- Exchange Connection ---
EXCHANGE_CONFIG = {
    'API_KEY': os.getenv('EXCHANGE_API_KEY', ''),
    'API_SECRET': os.getenv('EXCHANGE_API_SECRET', ''),
    'PASSWORD': os.getenv('EXCHANGE_API_PASSWORD', ''),
    # Sandbox mode for testing without real funds
    'SANDBOX_MODE': os.getenv('SANDBOX_MODE', 'True').lower() in ('true', '1', 't')
}

# --- Main Configuration Getter ---
def get_config():
    """
    Consolidates and returns the main configuration dictionary.
    """
    return {
        'trading': TRADING_CONFIG,
        'exchange': EXCHANGE_CONFIG,
    }

if __name__ == '__main__':
    # A simple way to print the config for debugging
    config = get_config()
    import json
    print(json.dumps(config, indent=4))
