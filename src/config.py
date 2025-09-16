"""
This module defines the configuration for the trading bot.

It consolidates settings for trading parameters, exchange connections,
notifications, and analysis modules. It also loads sensitive information
from a .env file.
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

def _load_analysis_config():
    """Loads the timeframe-specific analysis configuration from the JSON file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'analysis', 'analysis_config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return an empty dict with empty fallbacks if the file is missing or invalid
        return {"long_term": {}, "medium_term": {}, "short_term": {}}

ANALYSIS_SETTINGS_BY_GROUP = _load_analysis_config()

TRADING_CONFIG = {
    'EXCHANGE_ID': 'okx',
    'DEFAULT_SYMBOL': 'BTC/USDT',
    'PERIOD': '3mo', # Default data period for each timeframe
    'ACCOUNT_BALANCE': 10000,
    'MAX_RISK_PER_TRADE': 0.02,

    # List of currencies to be monitored and analyzed
    'WATCHLIST': [
        'BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'LINK-USDT', 'DOGE-USDT'
    ],

    # Timeframes to be analyzed in order
    'TIMEFRAMES_TO_ANALYZE': ['1D', '4H', '1H', '30m', '15m', '5m', '3m'],

    # Timeframe groups for different types of analysis
    'TIMEFRAME_GROUPS': {
        "long_term": ['1D', '4H', '1H'],
        "medium_term": ['30m', '15m'],
        "short_term": ['5m', '3m']
    }
}

EXCHANGE_CONFIG = {
    'API_KEY': os.getenv('EXCHANGE_API_KEY', ''),
    'API_SECRET': os.getenv('EXCHANGE_API_SECRET', ''),
    'PASSWORD': os.getenv('EXCHANGE_API_PASSWORD', ''),
    'SANDBOX_MODE': os.getenv('SANDBOX_MODE', 'False').lower() in ('true', '1', 't')
}

TELEGRAM_CONFIG = {
    'BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', '')
}

ANALYSIS_CONFIG = {
    # General
    'ATR_PERIOD': 14,

    # Trend Analysis
    'TREND_SHORT_PERIOD': 20,
    'TREND_MEDIUM_PERIOD': 50,
    'TREND_LONG_PERIOD': 100,

    # Channel Analysis
    'CHANNEL_LOOKBACK': 50,

    # S/R Analysis
    'SR_LOOKBACK': 100,
    'SR_TOLERANCE': 0.015,

    # Fibonacci Analysis
    'FIB_LOOKBACK': 90,

    # Pattern Analysis
    'PATTERN_LOOKBACK': 90,
    'PATTERN_PRICE_TOLERANCE': 0.03,

    # This will now be handled by the JSON config
}

OUTPUT_CONFIG = {
    'OUTPUT_FOLDER': 'analysis_reports',
    'FILENAME_FORMAT': '{symbol}_analysis_{timestamp}',
    'SAVE_JSON': True,
    'SAVE_TXT': True,
    'SAVE_CHARTS': False
}

RECOMMENDATION_CONFIG = {
    'SCORE_WEIGHTS': {
        'indicators': 1.5,
        'trends': 3.0,
        'channels': 1.0,
        'support_resistance': 2.0,
        'fibonacci': 1.0,
        'patterns': 3.0,
        'trend_lines': 1.5
    },
    'THRESHOLDS': {
        'strong_buy': 20,
        'buy': 10,
        'hold': -5,
        'sell': -15
    },
    'ACTIONS': {
        'strong_buy': "Strong Buy 🚀",
        'buy': "Buy 📈",
        'hold': "Wait ⏳",
        'sell': 'Sell 📉',
        'strong_sell': "Strong Sell 🔻"
    },
    'CONFIDENCE_LEVELS': {
        'strong_buy': 95,
        'buy': 85,
        'hold': 60,
        'sell': 85,
        'strong_sell': 95
    },
    'CONFLICT_NOTE_TEMPLATE': "Signal adjusted from '{original_action}' to '{new_action}' due to a strong forming {pattern_type} pattern ({pattern_name})."
}

def get_config():
    """Retrieves all configuration settings.

    Returns:
        Dict: A dictionary containing all configuration settings.
    """
    config = {
        'trading': TRADING_CONFIG,
        'exchange': EXCHANGE_CONFIG,
        'telegram': TELEGRAM_CONFIG,
        'analysis': ANALYSIS_CONFIG,
        'output': OUTPUT_CONFIG,
        'recommendation': RECOMMENDATION_CONFIG
    }
    # Merge the new group-specific settings into the main analysis config
    config['analysis']['groups'] = ANALYSIS_SETTINGS_BY_GROUP
    return config

def print_current_config():
    """Prints the current configuration to the console.

    This function is intended for debugging purposes.
    """
    pass

if __name__ == "__main__":
    print_current_config()
