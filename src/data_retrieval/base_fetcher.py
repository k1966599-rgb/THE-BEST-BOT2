from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

class BaseDataFetcher(ABC):
    """Abstract base class for data fetchers.

    This class defines the standard interface for fetching both historical
    and live market data from any data source.
    """

    @abstractmethod
    def fetch_historical_data(self, symbol: str, timeframe: str, days_to_fetch: int) -> List[Dict]:
        """Fetches historical candlestick data.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC-USDT').
            timeframe (str): The timeframe for the candles (e.g., '1h', '4h').
            days_to_fetch (int): The number of days of historical data to get.

        Returns:
            List[Dict]: A list of dictionaries, where each dictionary is a
            candlestick.
        """
        pass

    @abstractmethod
    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent cached price for a symbol.

        This method should return data from a local cache that is updated by a
        background process, without making a new network request.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC-USDT').

        Returns:
            Optional[Dict[str, Any]]: A dictionary with the latest price info,
            or None if not available.
        """
        pass

    @abstractmethod
    def start_data_services(self, symbols: List[str]):
        """Starts background services for data collection.

        This can include WebSocket clients for live price updates or other
        streaming services.

        Args:
            symbols (List[str]): A list of symbols to subscribe to.
        """
        pass

    @abstractmethod
    def stop(self):
        """Stops all running background services and cleans up resources."""
        pass
