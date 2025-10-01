import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from src.utils.symbol_util import normalize_symbol
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages reading and writing data by interfacing with the DatabaseManager.
    This class handles the logic of when to fetch from cache vs. when it's a miss.
    """
    def __init__(self, db_path: str = 'data/cache.db', default_ttl_hours: int = 24):
        self.db = DatabaseManager(db_path)
        self.default_ttl_hours = default_ttl_hours

    def get(self, symbol: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves fresh, valid data from the database cache.

        Returns:
            A list of candle data if fresh and valid data is found, otherwise None.
        """
        normalized_symbol = normalize_symbol(symbol)

        metadata = self.db.get_cache_metadata(normalized_symbol, timeframe)
        if not metadata:
            logger.info(f"Cache miss (no metadata) for {normalized_symbol}-{timeframe}")
            return None

        # Check TTL
        last_updated_str = metadata["last_updated"]
        ttl_hours = metadata["ttl_hours"]

        # Convert the timestamp string from the DB back to a datetime object
        last_updated = datetime.fromisoformat(last_updated_str)

        if datetime.utcnow() > last_updated + timedelta(hours=ttl_hours):
            logger.info(f"Cache expired for {normalized_symbol}-{timeframe}. Last updated: {last_updated}")
            return None

        candles = self.db.get_candles(normalized_symbol, timeframe)
        if not candles:
            logger.warning(f"Cache miss (no candles) for {normalized_symbol}-{timeframe} despite fresh metadata.")
            return None

        logger.info(f"Cache hit for {normalized_symbol}-{timeframe}")
        return candles

    def set(self, symbol: str, timeframe: str, data: List[Dict[str, Any]]):
        """
        Saves data to the database cache via the DatabaseManager.
        """
        if not data:
            logger.warning(f"Attempted to save empty data for {symbol} on {timeframe}. Aborting.")
            return

        normalized_symbol = normalize_symbol(symbol)
        self.db.save_candles(normalized_symbol, timeframe, data, self.default_ttl_hours)
        logger.info(f"Successfully saved data to DB cache for {normalized_symbol}-{timeframe}")