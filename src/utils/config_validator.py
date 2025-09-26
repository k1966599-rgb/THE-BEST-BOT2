from pydantic import BaseModel, Field
from typing import List, Dict, Any

class TelegramConfig(BaseModel):
    """Validates the Telegram settings."""
    TOKEN: str = Field(..., min_length=1, description="Telegram bot token cannot be empty.")
    ADMIN_CHAT_ID: str = Field(..., min_length=1, description="Telegram admin chat ID cannot be empty.")

class ExchangeConfig(BaseModel):
    """Validates the exchange connection settings."""
    API_KEY: str
    API_SECRET: str
    PASSWORD: str
    SANDBOX_MODE: bool

class TradingConfig(BaseModel):
    """Validates the trading parameters."""
    WATCHLIST: List[str]
    TIMEFRAMES: List[str]
    TIMEFRAME_GROUPS: Dict[str, List[str]]
    ANALYSIS_INTERVAL_MINUTES: int = Field(..., gt=0)

class CacheConfig(BaseModel):
    """Validates the cache settings."""
    ENABLED: bool
    DIRECTORY: str
    EXPIRATION_MINUTES: int

class FiboStrategyParams(BaseModel):
    """Validates parameters for the Fibo strategy."""
    rsi_period: int
    sma_period_fast: int
    sma_period_slow: int
    fib_lookback: int

class StrategyParams(BaseModel):
    """Validates the overall strategy parameters structure."""
    fibo_strategy: FiboStrategyParams

class UiConfig(BaseModel):
    """Validates the UI configuration structure."""
    MESSAGES: Dict[str, str]
    BUTTONS: Dict[str, str]
    CALLBACK_DATA: Dict[str, str]

class AppSettings(BaseModel):
    """The main model for validating the entire application configuration."""
    trading: TradingConfig
    exchange: ExchangeConfig
    risk_management: Dict[str, Any]  # Less strict for now
    strategy_params: StrategyParams
    telegram: TelegramConfig
    cache: CacheConfig
    ui: UiConfig

def validate_config(config_dict: Dict[str, Any]) -> AppSettings:
    """
    Validates the configuration dictionary against the Pydantic models.

    This function acts as the single entry point for configuration validation.

    Raises:
        pydantic.ValidationError: If the configuration is invalid.
    """
    return AppSettings.model_validate(config_dict)