#!/usr/bin/env python3
import asyncio
import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import time
import threading

from .base_fetcher import BaseDataFetcher
from .okx_websocket_client import OKXWebSocketClient


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('okx_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OKXDataFetcher(BaseDataFetcher):
    """Fetches historical and live data from the OKX exchange.

    This class implements the BaseDataFetcher interface for the OKX exchange.
    It handles fetching historical data via REST API, manages a WebSocket
    client for live data streams, and includes a multi-level caching
    system (in-memory and file-based).
    """
    def __init__(self, config: Dict, data_dir: str = 'data'):
        """Initializes the OKXDataFetcher.

        Args:
            config (Dict): The main configuration dictionary.
            data_dir (str, optional): The directory to store cached data.
                Defaults to 'data'.
        """
        self.config = config
        self.base_url = 'https://www.okx.com'
        self.data_dir = Path(data_dir)
        self.price_cache = {}
        self.historical_cache = {}
        self._stop_event = threading.Event()

        self.websocket_client = OKXWebSocketClient(
            config=self.config,
            price_cache=self.price_cache
        )
        self._ensure_data_directory()
        logger.info(f"📁 OKX Data Fetcher initialized - Data Dir: {self.data_dir}")

    def _ensure_data_directory(self):
        """Ensures that the data storage directory exists."""
        try:
            self.data_dir.mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"❌ Error creating data directory {self.data_dir}: {e}")

    def fetch_current_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetches current prices via REST API.

        Note: This is a placeholder and is not currently implemented. Live
        price data is handled by the WebSocket client.

        Args:
            symbols (Optional[List[str]], optional): A list of symbols to
                fetch. Defaults to None.

        Returns:
            Dict[str, Any]: An empty dictionary.
        """
        return {}

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Converts a timeframe string to an integer number of minutes.

        Args:
            timeframe (str): The timeframe string (e.g., '5m', '1H', '1D').

        Returns:
            int: The equivalent number of minutes. Defaults to 1440 (1 day)
            if the format is unrecognized.
        """
        try:
            if 'm' in timeframe:
                return int(timeframe.replace('m', ''))
            elif 'H' in timeframe:
                return int(timeframe.replace('H', '')) * 60
            elif 'D' in timeframe:
                return int(timeframe.replace('D', '')) * 24 * 60
        except (ValueError, TypeError):
            return 1440
        return 1440

    def _get_timeframe_group(self, timeframe: str) -> str:
        """Determines the timeframe group from the timeframe string.

        This is used for organizing cached data into directories.

        Args:
            timeframe (str): The timeframe string (e.g., '1h').

        Returns:
            str: The name of the group (e.g., 'short_term', 'medium_term').
        """
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        for group, timeframes in timeframe_groups.items():
            if timeframe in timeframes:
                return group
        return "other"

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """Constructs the file path for storing historical data.

        Args:
            symbol (str): The trading symbol.
            timeframe (str): The timeframe string.

        Returns:
            Path: The full Path object for the data file.
        """
        symbol_dir = symbol.replace('/', '-')
        timeframe_group = self._get_timeframe_group(timeframe)
        return self.data_dir / symbol_dir / timeframe_group / f"{timeframe}.json"

    def _read_from_cache(self, cache_key: tuple) -> Optional[Dict[str, Any]]:
        """Reads historical data from the in-memory cache.

        Args:
            cache_key (tuple): The key for the in-memory cache, typically
                (symbol, timeframe, days_to_fetch).

        Returns:
            Optional[Dict[str, Any]]: The cached data, or None if not found.
        """
        if cache_key in self.historical_cache:
            logger.info(f"✅ Found historical data for {cache_key} in cache.")
            return self.historical_cache[cache_key]
        return None

    def _read_from_file(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Reads historical data from a JSON file.

        Args:
            symbol (str): The trading symbol.
            timeframe (str): The timeframe string.

        Returns:
            Optional[Dict[str, Any]]: The data loaded from the file, or None
            if the file doesn't exist or an error occurs.
        """
        file_path = self._get_file_path(symbol, timeframe)
        if file_path.exists():
            logger.info(f"💾 Loading historical data for {symbol} ({timeframe}) from {file_path}...")
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"❌ Error reading historical data file {file_path}: {e}")
        return None

    def _save_to_file(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Saves historical data to a JSON file.

        Args:
            symbol (str): The trading symbol.
            timeframe (str): The timeframe string.
            data (Dict[str, Any]): The data to be saved.
        """
        file_path = self._get_file_path(symbol, timeframe)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved historical data for {symbol} ({timeframe}) to {file_path}")
        except IOError as e:
            logger.error(f"❌ Error saving historical data file {file_path}: {e}")

    def _fetch_from_network(self, symbol: str, timeframe: str, days_to_fetch: int) -> List[List[str]]:
        """Fetches raw candlestick data from the OKX REST API.

        This method handles pagination to retrieve the required number of
        candles and includes a retry mechanism for network requests.

        Args:
            symbol (str): The trading symbol.
            timeframe (str): The timeframe string.
            days_to_fetch (int): The number of days of data to retrieve.

        Returns:
            List[List[str]]: A list of raw candle data from the API, or an
            empty list if the fetch fails.
        """
        logger.info(f"📊 Fetching historical data for {symbol} ({timeframe}) for {days_to_fetch} days from network...")
        all_candles = []
        current_before_ts = None
        endpoint_url = f"{self.base_url}/api/v5/market/candles"
        limit_per_request = 300

        tf_minutes = self._timeframe_to_minutes(timeframe)
        total_candles_needed = (days_to_fetch * 24 * 60) / tf_minutes

        while len(all_candles) < total_candles_needed:
            remaining_candles = int(total_candles_needed - len(all_candles))
            limit = min(limit_per_request, remaining_candles)
            params = {'instId': symbol, 'bar': timeframe, 'limit': str(limit)}

            if current_before_ts:
                params['before'] = current_before_ts

            max_retries = 3
            candles_data = None
            for attempt in range(max_retries):
                try:
                    response = requests.get(endpoint_url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
                    response.raise_for_status()
                    data = response.json()
                    if data.get('code') == '0':
                        candles_data = data.get('data', [])
                        if not candles_data:
                            logger.info(f"⏹️ No more historical data from API for {symbol}.")
                        break

                    else:
                        raise requests.exceptions.RequestException(f"API Error: {data.get('msg', 'Unknown error')}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ Attempt {attempt + 1} of {max_retries} failed for {symbol}: {e}")
                    if attempt + 1 == max_retries:
                        logger.error(f"❌ All {max_retries} attempts failed. Aborting fetch for this timeframe.")
                        return []
                    time.sleep(5 * (attempt + 1))

            if not candles_data:
                break

            all_candles.extend(candles_data)
            current_before_ts = candles_data[-1][0]
            time.sleep(0.5)

        return all_candles

    def _process_candles(self, raw_candles: List[List[str]], symbol: str) -> Dict[str, Any]:
        """Processes raw candle data into a structured format.

        This method converts the raw list-based candle data from the API into
        a more readable list of dictionaries, adding derived information like
        candle shape and tail sizes. It also ensures uniqueness of timestamps.

        Args:
            raw_candles (List[List[str]]): The raw candle data from the API.
            symbol (str): The trading symbol.

        Returns:
            Dict[str, Any]: A dictionary containing the processed candle data,
            symbol, and last update time.
        """
        historical_data = []
        seen_timestamps = set()
        for candle in raw_candles:
            timestamp = int(candle[0])
            if timestamp in seen_timestamps:
                continue

            o, h, l, c, v = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4]), float(candle[5])

            body_length = abs(c - o)
            upper_tail = h - max(o, c)
            lower_tail = min(o, c) - l

            shape = 'doji'
            if body_length > 0.0001:
                shape = 'bullish' if c > o else 'bearish'

            historical_data.append({
                'timestamp': timestamp, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v,
                'date': datetime.fromtimestamp(timestamp / 1000).isoformat(),
                'body_length': body_length,
                'upper_tail': upper_tail,
                'lower_tail': lower_tail,
                'shape': shape
            })
            seen_timestamps.add(timestamp)

        historical_data.sort(key=lambda x: x['timestamp'])

        return {
            'symbol': symbol.replace('-', '/'),
            'last_update': datetime.now().isoformat(),
            'data': historical_data
        }

    def fetch_historical_data(self, symbol: str = 'BTC-USDT', timeframe: str = '1D', days_to_fetch: int = 730) -> Dict[str, Any]:
        """Fetches historical data, utilizing a multi-level cache.

        This method orchestrates the fetching process, following a
        cache-then-network strategy:
        1. Check the in-memory cache.
        2. Check the file system cache.
        3. Fetch from the network API if not found in any cache.
        The result is then stored in both caches for future requests.

        Args:
            symbol (str, optional): The trading symbol. Defaults to 'BTC-USDT'.
            timeframe (str, optional): The timeframe string. Defaults to '1D'.
            days_to_fetch (int, optional): The number of days to fetch.
                Defaults to 730.

        Returns:
            Dict[str, Any]: The processed historical data, or an empty dict
            if fetching fails.
        """
        cache_key = (symbol, timeframe, days_to_fetch)

        cached_data = self._read_from_cache(cache_key)
        if cached_data:
            return cached_data

        file_data = self._read_from_file(symbol, timeframe)
        if file_data:
            self.historical_cache[cache_key] = file_data
            return file_data

        raw_candles = self._fetch_from_network(symbol, timeframe, days_to_fetch)
        if not raw_candles:
            return {}

        processed_data = self._process_candles(raw_candles, symbol)

        self.historical_cache[cache_key] = processed_data
        self._save_to_file(symbol, timeframe, processed_data)

        logger.info(f"✅ Fetched and cached {len(processed_data['data'])} unique candles for {symbol}")
        return processed_data

    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent price data from the live cache.

        Args:
            symbol (str): The trading symbol.

        Returns:
            Optional[Dict[str, Any]]: The latest price data dictionary, or
            None if not found.
        """
        return self.price_cache.get(symbol)

    def start_data_services(self, symbols: List[str]):
        """Starts the WebSocket client for live data collection.

        Args:
            symbols (List[str]): A list of symbols to subscribe to.
        """
        logger.info("🚀 Starting all data services...")
        self.websocket_client.start(symbols)
        logger.info("✅ WebSocket client started.")

    def stop(self):
        """Stops the data fetcher and its background services.

        This method sets a threading event to signal the WebSocket client
        to terminate its connection and stop running.
        """
        logger.info("⏹️ Stopping data fetcher...")
        self.websocket_client.stop()
        self._stop_event.set()
        logger.info("✅ Stop signal sent.")
