import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages all interactions with the SQLite database for caching.
    """
    def __init__(self, db_path: str = 'data/cache.db'):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_db()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database {self.db_path}: {e}")
            raise

    def _init_db(self):
        """Initializes the database schema if it doesn't exist."""
        if not self._conn:
            return
        try:
            with self._conn:
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS candles (
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        timestamp INTEGER NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        PRIMARY KEY (symbol, timeframe, timestamp)
                    )
                ''')
                self._conn.execute('''
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        last_updated TIMESTAMP NOT NULL,
                        ttl_hours INTEGER NOT NULL,
                        PRIMARY KEY (symbol, timeframe)
                    )
                ''')
            logger.info("Database tables initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database tables: {e}")

    def get_candles(self, symbol: str, timeframe: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieves candle data from the database."""
        if not self._conn:
            return []
        try:
            with self._conn:
                cursor = self._conn.execute(
                    '''
                    SELECT timestamp, open, high, low, close, volume FROM candles
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    ''',
                    (symbol, timeframe, limit)
                )
                rows = cursor.fetchall()
                # Return in ascending order as expected by analyzers
                return [dict(row) for row in reversed(rows)]
        except sqlite3.Error as e:
            logger.error(f"Error getting candles for {symbol}-{timeframe}: {e}")
            return []

    def save_candles(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]], ttl_hours: int):
        """Saves a batch of candle data to the database, ignoring duplicates."""
        if not self._conn or not candles:
            return

        candle_data = [
            (symbol, timeframe, int(c['timestamp']), float(c['open']), float(c['high']), float(c['low']), float(c['close']), float(c['volume']))
            for c in candles
        ]

        try:
            with self._conn:
                self._conn.executemany(
                    '''
                    INSERT OR IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    candle_data
                )
            self.update_cache_metadata(symbol, timeframe, ttl_hours)
        except sqlite3.Error as e:
            logger.error(f"Error saving candles for {symbol}-{timeframe}: {e}")

    def get_cache_metadata(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Retrieves cache metadata for a given symbol and timeframe."""
        if not self._conn:
            return None
        try:
            with self._conn:
                cursor = self._conn.execute(
                    'SELECT last_updated, ttl_hours FROM cache_metadata WHERE symbol = ? AND timeframe = ?',
                    (symbol, timeframe)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting metadata for {symbol}-{timeframe}: {e}")
            return None

    def update_cache_metadata(self, symbol: str, timeframe: str, ttl_hours: int):
        """Updates or inserts cache metadata."""
        if not self._conn:
            return
        try:
            with self._conn:
                self._conn.execute(
                    '''
                    INSERT OR REPLACE INTO cache_metadata (symbol, timeframe, last_updated, ttl_hours)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (symbol, timeframe, datetime.utcnow(), ttl_hours)
                )
        except sqlite3.Error as e:
            logger.error(f"Error updating metadata for {symbol}-{timeframe}: {e}")

    def close(self):
        """Closes the database connection."""
        if self._conn:
            self._conn.close()
            logger.info("Database connection closed.")