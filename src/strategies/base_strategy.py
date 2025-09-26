from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    All strategies should inherit from this class and implement the
    `get_analysis` method.
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
    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Generates a trading analysis based on the input data.

        This method must be implemented by all subclasses.

        Args:
            data (pd.DataFrame): A pandas DataFrame containing the market data.
            symbol (str): The trading symbol (e.g., 'BTC-USDT').
            timeframe (str): The timeframe for the candles (e.g., '1H', '4H').

        Returns:
            Dict[str, Any]: A dictionary containing the detailed analysis result.
                            The structure may vary but should contain at least a 'signal'.
        """
        pass
