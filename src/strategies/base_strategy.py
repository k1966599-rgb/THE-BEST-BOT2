from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    All strategies should inherit from this class and implement the
    `generate_signals` method.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the base strategy.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration parameters
                                     for the strategy.
        """
        self.config = config

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, str]:
        """
        Generates trading signals based on the input data.

        This method must be implemented by all subclasses.

        Args:
            data (pd.DataFrame): A pandas DataFrame containing the market data
                                 (e.g., OHLCV candles).

        Returns:
            Dict[str, str]: A dictionary containing the trading signal.
                            For example: {'signal': 'BUY', 'reason': 'RSI below 30'}
                            Possible signals: 'BUY', 'SELL', 'HOLD'.
        """
        pass
