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
    },

    # The amount of the base currency to trade (e.g., for BTC-USDT, this is the amount of BTC)
    # NOTE: Ensure this amount is valid for the exchange's minimum trade size.
    'TRADE_AMOUNT': '0.001',

    # Interval for periodic analysis in minutes
    'ANALYSIS_INTERVAL_MINUTES': 15,

    # --- Candle Fetching Limits ---
    # Defines how many candles to fetch for analysis.
    # 'default' is used for any timeframe not explicitly listed.
    'CANDLE_FETCH_LIMITS': {
        'default': 1000,
        '1D': 360
    },

    # Defines the parent timeframe for Multi-Timeframe Analysis (MTA)
    # The key is the child, the value is the parent.
    # Timeframes without a parent (e.g., '1D') are considered the highest level.
    'TIMEFRAME_HIERARCHY': {
        '3m': '15m',
        '5m': '30m',
        '15m': '1H',
        '30m': '4H',
        '1H': '4H',
        '4H': '1D',
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

# --- Risk Management Settings ---
# These are example values. Tune them based on your risk tolerance.
RISK_MANAGEMENT_CONFIG = {
    'max_drawdown': 150.5,       # Maximum unrealized loss in quote currency (e.g., USDT) before closing
    'stop_loss_percentage': 5.0, # A fallback stop-loss percentage if not otherwise defined
    'atr_multiplier_sl': 2.0,    # Multiplier for ATR to set stop-loss
    'atr_multiplier_tp': 4.0     # Multiplier for ATR to set take-profit
}

# --- Strategy-Specific Parameters ---
# This makes it easy to tune strategies without changing the code.
STRATEGY_PARAMS = {
    'fibo_strategy': {
        'rsi_period': 14,
        'sma_period_fast': 50,
        'sma_period_slow': 200,
        'fib_lookback': 50,
        'swing_lookback_period': 50,
        'adx_trend_threshold': 25,
        'signal_threshold': 5, # Minimum score required to generate a BUY/SELL signal
        'require_adx_confirmation': True, # If True, a signal is only generated if ADX is above the threshold
        'swing_prominence_atr_multiplier': 0.5, # Multiplier for ATR to determine swing point prominence
        'volume_spike_multiplier': 2.0, # How much higher volume needs to be than its average to be a "spike"
        'scoring_weights': {
            'confluence_zone': 2,
            'rsi_confirm': 1,
            'macd_confirm': 1,
            'stoch_confirm': 1,
            'reversal_pattern': 2,
            'volume_spike': 2
        },
        # --- Timeframe-Specific Overrides ---
        'timeframe_overrides': {
            '1D': {
                'sma_period_slow': 50,
                'swing_lookback_period': 40
            }
        }
    }
}


# --- Telegram Bot Settings ---
TELEGRAM_CONFIG = {
    'TOKEN': os.getenv('BOT_TOKEN', ''),
    'ADMIN_CHAT_ID': os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')
}


# --- Main Configuration Getter ---
def get_config():
    """
    Consolidates and returns the main configuration dictionary.
    """
    return {
        'trading': TRADING_CONFIG,
        'exchange': EXCHANGE_CONFIG,
        'risk_management': RISK_MANAGEMENT_CONFIG,
        'strategy_params': STRATEGY_PARAMS,
        'telegram': TELEGRAM_CONFIG
    }

if __name__ == '__main__':
    # A simple way to print the config for debugging
    config = get_config()
    import json
    print(json.dumps(config, indent=4))