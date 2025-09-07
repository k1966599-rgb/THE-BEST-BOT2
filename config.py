"""
ملف التكوين السريع للبوت
قم بتعديل القيم أدناه حسب احتياجاتك
"""
import os
from dotenv import load_dotenv

load_dotenv()

TRADING_CONFIG = {
    'EXCHANGE_ID': 'okx',
    'DEFAULT_SYMBOL': 'BTC/USDT',
    'PERIOD': '3mo', # الفترة الافتراضية للبيانات لكل فريم
    'ACCOUNT_BALANCE': 10000,
    'MAX_RISK_PER_TRADE': 0.02,

    # الفريمات الزمنية التي سيتم تحليلها بالترتيب
    'TIMEFRAMES_TO_ANALYZE': ['1d', '4h', '1h', '30m', '15m', '5m', '3m'],

    # مجموعات الفريمات الزمنية لأنواع التحليل المختلفة
    'TIMEFRAME_GROUPS': {
        "long": ['1d', '4h', '1h'],
        "medium": ['30m', '15m'],
        "short": ['5m', '3m', '1m']
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

    # Timeframe-specific overrides for analysis parameters
    'TIMEFRAME_OVERRIDES': {
        '1d': {
            'SR_LOOKBACK': 365,
            'FIB_LOOKBACK': 365,
            'PATTERN_LOOKBACK': 365,
            'CHANNEL_LOOKBACK': 180,
        },
        '4h': {
            'SR_LOOKBACK': 1080, # 180 days
            'FIB_LOOKBACK': 1080,
            'PATTERN_LOOKBACK': 1080,
            'CHANNEL_LOOKBACK': 360, # 60 days
        },
    }
}

WATCHLIST = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT',
    'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'BNB/USDT', 'MATIC/USDT'
]

OUTPUT_CONFIG = {
    'OUTPUT_FOLDER': 'analysis_reports',
    'FILENAME_FORMAT': '{symbol}_analysis_{timestamp}',
    'SAVE_JSON': True,
    'SAVE_TXT': True,
    'SAVE_CHARTS': False
}

def get_config():
    """استرجاع جميع الإعدادات"""
    return {
        'trading': TRADING_CONFIG,
        'exchange': EXCHANGE_CONFIG,
        'telegram': TELEGRAM_CONFIG,
        'analysis': ANALYSIS_CONFIG,
        'watchlist': WATCHLIST,
        'output': OUTPUT_CONFIG
    }

def print_current_config():
    pass

if __name__ == "__main__":
    print_current_config()
