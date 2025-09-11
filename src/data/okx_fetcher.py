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
    """
    Fetches historical and REST-based data from OKX.
    Manages the WebSocket client for live data.
    """
    def __init__(self, config: Dict, data_dir: str = 'okx_data'):
        self.config = config
        self.base_url = 'https://www.okx.com'
        self.data_dir = Path(data_dir)
        self.price_cache = {}
        self.historical_cache = {}
        self._stop_event = threading.Event()

        self.websocket_client = OKXWebSocketClient(
            config=self.config,
            price_cache=self.price_cache,
            stop_event=self._stop_event
        )
        self.default_symbols = self.config.get('trading', {}).get('DEFAULT_SYMBOLS', [])
        self._ensure_data_directory()
        logger.info(f"📁 OKX Data Fetcher initialized - Data Dir: {self.data_dir}")

    def _ensure_data_directory(self):
        try:
            self.data_dir.mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"❌ Error creating data directory {self.data_dir}: {e}")

    def fetch_current_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetches current prices via REST API."""
        # ... [implementation unchanged] ...
        return {}

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Converts a timeframe string (e.g., '5m', '1H', '1D') to minutes.
        """
        try:
            if 'm' in timeframe:
                return int(timeframe.replace('m', ''))
            elif 'H' in timeframe: # OKX uses 'H' for hour
                return int(timeframe.replace('H', '')) * 60
            elif 'D' in timeframe: # OKX uses 'D' for day
                return int(timeframe.replace('D', '')) * 24 * 60
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timeframe '{timeframe}', defaulting to 1440 minutes (1 day).")
            return 1440 # Default to 1 day

        logger.warning(f"Unknown timeframe format '{timeframe}', defaulting to 1440 minutes (1 day).")
        return 1440

    def _read_from_cache(self, cache_key: tuple) -> Optional[Dict[str, Any]]:
        """Reads data from the in-memory cache."""
        if cache_key in self.historical_cache:
            logger.info(f"✅ Found historical data for {cache_key} in cache.")
            return self.historical_cache[cache_key]
        return None

    def _read_from_file(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Reads data from a local JSON file."""
        file_path = Path(f"{symbol}_{timeframe}_historical.json")
        if file_path.exists():
            logger.info(f"💾 Loading historical data for {symbol} from {file_path}...")
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"❌ Error reading historical data file {file_path}: {e}")
        return None

    def _save_to_file(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """Saves data to a local JSON file."""
        file_path = Path(f"{symbol}_{timeframe}_historical.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"💾 Saved historical data for {symbol} to {file_path}")
        except IOError as e:
            logger.error(f"❌ Error saving historical data file {file_path}: {e}")

    def _fetch_from_network(self, symbol: str, timeframe: str, days_to_fetch: int) -> List[List[str]]:
        """Fetches raw candle data from the OKX API."""
        logger.info(f"📊 Fetching historical data for {symbol} ({timeframe}) for {days_to_fetch} days from network...")
        all_candles = []
        current_before_ts = None
        endpoint_url = f"{self.base_url}/api/v5/market/candles"
        limit_per_request = 300
        tf_minutes = self._timeframe_to_minutes(timeframe)
        if tf_minutes <= 0: tf_minutes = 1440
        total_candles_needed = (days_to_fetch * 24 * 60) / tf_minutes
        max_requests = 20

        while len(all_candles) < total_candles_needed and max_requests > 0:
            params = {'instId': symbol, 'bar': timeframe, 'limit': str(limit_per_request)}
            if current_before_ts:
                params['before'] = current_before_ts
            try:
                response = requests.get(endpoint_url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                response.raise_for_status()
                data = response.json()
                if data.get('code') == '0':
                    candles_data = data.get('data', [])
                    if not candles_data:
                        logger.info(f"⏹️ No more historical data from API for {symbol}.")
                        break
                    all_candles.extend(candles_data)
                    current_before_ts = candles_data[-1][0]
                    time.sleep(0.3)
                else:
                    raise requests.exceptions.RequestException(f"API Error: {data.get('msg', 'Unknown error')}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ HTTP Error fetching historical data for {symbol}: {e}")
                return []
            finally:
                max_requests -= 1

        if max_requests == 0:
            logger.warning(f"⚠️ Hit max request limit for {symbol}. Data may be incomplete.")

        return all_candles

    def _process_candles(self, raw_candles: List[List[str]], symbol: str) -> Dict[str, Any]:
        """Processes raw candle data and wraps it in the standard format."""
        historical_data = []
        seen_timestamps = set()
        for candle in raw_candles:
            timestamp = int(candle[0])
            if timestamp not in seen_timestamps:
                historical_data.append({
                    'timestamp': timestamp, 'open': float(candle[1]), 'high': float(candle[2]),
                    'low': float(candle[3]), 'close': float(candle[4]), 'volume': float(candle[5]),
                    'date': datetime.fromtimestamp(timestamp / 1000).isoformat()
                })
                seen_timestamps.add(timestamp)

        historical_data.sort(key=lambda x: x['timestamp'])

        return {
            'symbol': symbol.replace('-', '/'),
            'last_update': datetime.now().isoformat(),
            'data': historical_data
        }

    def fetch_historical_data(self, symbol: str = 'BTC-USDT', timeframe: str = '1D', days_to_fetch: int = 365) -> Dict[str, Any]:
        """
        Fetches historical data, checking local JSON files and in-memory cache first.
        """
        cache_key = (symbol, timeframe, days_to_fetch)

        # 1. Check in-memory cache
        cached_data = self._read_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 2. Check local file
        file_data = self._read_from_file(symbol, timeframe)
        if file_data:
            self.historical_cache[cache_key] = file_data
            return file_data

        # 3. Fetch from network
        raw_candles = self._fetch_from_network(symbol, timeframe, days_to_fetch)
        if not raw_candles:
            return {}

        processed_data = self._process_candles(raw_candles, symbol)

        # 4. Cache and save the new data
        self.historical_cache[cache_key] = processed_data
        self._save_to_file(symbol, timeframe, processed_data)

        logger.info(f"✅ Fetched and cached {len(processed_data['data'])} unique candles for {symbol}")
        return processed_data

    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.price_cache.get(symbol)

    def start_data_services(self, symbols: List[str] = None):
        """Starts background services for data collection."""
        if symbols is None:
            symbols = self.default_symbols
        logger.info("🚀 Starting all data services...")
        self.websocket_client.start(symbols)
        logger.info("✅ WebSocket client started.")

    def stop(self):
        """Signals all running threads to stop."""
        logger.info("⏹️ Stopping data fetcher...")
        self._stop_event.set()
        logger.info("✅ Stop signal sent.")
