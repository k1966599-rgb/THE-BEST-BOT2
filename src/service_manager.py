import logging
from typing import List
from .data.okx_fetcher import OKXDataFetcher

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self, fetcher: OKXDataFetcher):
        self.fetcher = fetcher

    def start_services(self, symbols: List[str]):
        """Starts all background services."""
        logger.info("🚀 Starting all background services...")
        self.fetcher.start_data_services(symbols)
        logger.info("✅ All background services started.")

    def stop_services(self):
        """Stops all background services."""
        logger.info("⏹️ Stopping all background services...")
        self.fetcher.stop()
        logger.info("✅ All background services stopped.")
