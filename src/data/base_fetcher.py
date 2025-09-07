from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

class BaseDataFetcher(ABC):
    """
    Abstract base class for data fetchers. It defines the standard interface
    for fetching historical and live market data.
    """

    @abstractmethod
    def fetch_historical_data(self, symbol: str, timeframe: str, days_to_fetch: int) -> List[Dict]:
        """
        Fetches historical candlestick data for a given symbol and timeframe.

        :param symbol: The trading symbol (e.g., 'BTC-USDT').
        :param timeframe: The timeframe for the candles (e.g., '1h', '4h', '1d').
        :param days_to_fetch: The number of days of historical data to retrieve.
        :return: A list of dictionaries, where each dictionary represents a candle.
        """
        pass

    @abstractmethod
    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent cached price for a symbol.

        This method should not make a network request but should return data
        from a local cache that is updated by a background process.

        :param symbol: The trading symbol (e.g., 'BTC-USDT').
        :return: A dictionary containing the latest price information or None if not available.
        """
        pass

    @abstractmethod
    def start_data_services(self, symbols: List[str]):
        """
        Starts any background services required for data collection, such as
        WebSocket clients for live price updates.

        :param symbols: A list of symbols to subscribe to.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stops all running background services and cleans up resources.
        """
        pass
