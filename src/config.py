"""
This module provides a centralized, validated configuration for the application.

It imports the validated AppSettings object and transforms it into the nested
dictionary structure that the rest of the application expects. This acts as an
adapter layer between the flat .env structure and the application's structured config.
"""
import json

def get_config():
    """
    Constructs and returns the application's configuration dictionary from the
    validated Pydantic settings object.
    """
    from .settings import settings
    # Manually construct the nested dictionaries that the application expects.
    # This keeps the validation flat and simple, while maintaining the app's
    # existing config structure.

    # Note: Pydantic automatically handles default values for missing optional fields.

    # Dynamically create a flat list of all timeframes from the groups
    timeframe_groups = settings.TIMEFRAME_GROUPS
    all_timeframes = [tf for group in timeframe_groups.values() for tf in group]

    config = {
        'telegram': {
            'TOKEN': settings.BOT_TOKEN,
            'ADMIN_CHAT_ID': settings.TELEGRAM_ADMIN_CHAT_ID
        },
        'exchange': {
            'API_KEY': settings.EXCHANGE_API_KEY,
            'API_SECRET': settings.EXCHANGE_API_SECRET,
            'PASSWORD': settings.EXCHANGE_API_PASSWORD,
            'SANDBOX_MODE': settings.SANDBOX_MODE
        },
        'trading': {
            'WATCHLIST': settings.WATCHLIST,
            'TIMEFRAME_GROUPS': timeframe_groups,
            'TIMEFRAMES': all_timeframes,  # Add the generated flat list
            'TIMEFRAME_HIERARCHY': settings.TIMEFRAME_HIERARCHY,
            'CANDLE_FETCH_LIMITS': settings.CANDLE_FETCH_LIMITS,
            'ANALYSIS_INTERVAL_MINUTES': settings.ANALYSIS_INTERVAL_MINUTES,
            'TRADE_AMOUNT': settings.TRADE_AMOUNT
        },
        'risk_management': {
            'max_drawdown': settings.MAX_DRAWDOWN,
            'stop_loss_percentage': settings.STOP_LOSS_PERCENTAGE,
            'atr_multiplier_sl': settings.ATR_MULTIPLIER_SL,
            'atr_multiplier_tp': settings.ATR_MULTIPLIER_TP
        },
        'strategy_params': {
            'fibo_strategy': {
                'rsi_period': settings.RSI_PERIOD,
                'sma_period_fast': settings.SMA_PERIOD_FAST,
                'sma_period_slow': settings.SMA_PERIOD_SLOW,
                'fib_lookback': settings.FIB_LOOKBACK,
                'swing_lookback_period': settings.SWING_LOOKBACK_PERIOD,
                'swing_comparison_window': settings.SWING_COMPARISON_WINDOW,
                'adx_trend_threshold': settings.ADX_TREND_THRESHOLD,
                'signal_threshold': settings.SIGNAL_THRESHOLD,
                'require_adx_confirmation': settings.REQUIRE_ADX_CONFIRMATION,
                'swing_prominence_atr_multiplier': settings.SWING_PROMINENCE_ATR_MULTIPLIER,
                'volume_spike_multiplier': settings.VOLUME_SPIKE_MULTIPLIER,
                # Pydantic models for nested structures are not easily representable here
                # in the flat structure, so we'll leave them as defaults for now.
                # A more advanced setup could handle this, but this solves the immediate validation issue.
                'scoring_weights': {
                    'confluence_zone': 2, 'rsi_confirm': 1, 'macd_confirm': 1,
                    'stoch_confirm': 1, 'reversal_pattern': 2, 'volume_spike': 2
                },
                'timeframe_overrides': {
                    '1D': {'sma_period_slow': 50, 'swing_lookback_period': 40}
                }
            }
        }
    }
    return config

if __name__ == '__main__':
    # To run this script directly for testing, you must execute it as a module
    # from the project root directory: python -m src.config
    import sys
    import os
    # Add the project root to the Python path to resolve src.* imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    # Now that the path is fixed, we can call get_config
    config = get_config()
    print(json.dumps(config, indent=4))