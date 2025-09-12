import logging
from typing import List
from .data.okx_fetcher import OKXDataFetcher

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages the lifecycle of background services.

    This class provides a simple interface to start and stop all background
    services required by the application, such as data fetchers.
    """
    def __init__(self, fetcher: OKXDataFetcher):
        """Initializes the ServiceManager.

        Args:
            fetcher (OKXDataFetcher): An instance of the data fetcher service.
        """
        self.fetcher = fetcher

    def start_services(self, symbols: List[str]):
        """Starts all background services.

        Args:
            symbols (List[str]): The list of symbols for which to start
                data services.
        """
        logger.info("🚀 Starting all background services...")
        self.fetcher.start_data_services(symbols)
        logger.info("✅ All background services started.")

    def stop_services(self):
        """Stops all background services."""
        logger.info("⏹️ Stopping all background services...")
        self.fetcher.stop()
        logger.info("✅ All background services stopped.")
