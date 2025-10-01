from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Optional

class AppSettings(BaseSettings):
    """
    Defines and validates all environment variables for the application.
    This model reads a flat structure from the .env file.
    """
    # Telegram
    BOT_TOKEN: str
    TELEGRAM_ADMIN_CHAT_ID: Optional[int] = None

    # Exchange
    EXCHANGE_API_KEY: str
    EXCHANGE_API_SECRET: str
    EXCHANGE_API_PASSWORD: str
    SANDBOX_MODE: bool = True

    # Trading - with default values
    WATCHLIST: List[str] = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'LINK/USDT', 'DOGE/USDT']
    TIMEFRAME_GROUPS: Dict[str, List[str]] = {
        "long_term": ["1D", "4h"], "medium_term": ["1h", "30m"], "short_term": ["15m", "5m"]
    }
    TIMEFRAME_HIERARCHY: Dict[str, str] = {
        '3m': '15m', '5m': '30m', '15m': '1H', '30m': '4H', '1H': '4H', '4H': '1D'
    }
    CANDLE_FETCH_LIMITS: Dict[str, int] = {
        "default": 250,
        "1D": 360
    }
    ANALYSIS_INTERVAL_MINUTES: int = 15
    TRADE_AMOUNT: str = "0.001"

    # Risk Management - with default values
    MAX_DRAWDOWN: float = 150.5
    STOP_LOSS_PERCENTAGE: float = 5.0
    ATR_MULTIPLIER_SL: float = 2.0
    ATR_MULTIPLIER_TP: float = 4.0

    # Strategy Params - with default values
    RSI_PERIOD: int = 14
    SMA_PERIOD_FAST: int = 20
    SMA_PERIOD_SLOW: int = 50
    FIB_LOOKBACK: int = 50
    SWING_LOOKBACK_PERIOD: int = 50
    SWING_COMPARISON_WINDOW: int = 5
    ADX_TREND_THRESHOLD: int = 25
    SIGNAL_THRESHOLD: int = 5
    REQUIRE_ADX_CONFIRMATION: bool = True
    SWING_PROMINENCE_ATR_MULTIPLIER: float = 0.5
    VOLUME_SPIKE_MULTIPLIER: float = 2.0

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from .env to prevent errors
    )

try:
    # This single settings object will be imported by the config module.
    settings = AppSettings()
except Exception as e:
    print(f"FATAL: Configuration error - {e}")
    raise