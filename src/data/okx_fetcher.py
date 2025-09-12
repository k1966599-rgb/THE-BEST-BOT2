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
    def __init__(self, config: Dict, data_dir: str = 'data'):
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
        return {}

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Converts a timeframe string (e.g., '5m', '1H', '1D') to minutes.
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
        """Determines the timeframe group from the timeframe string."""
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        for group, timeframes in timeframe_groups.items():
            if timeframe in timeframes:
                return group
        return "other"

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """Constructs the file path for storing historical data."""
        symbol_dir = symbol.replace('/', '-')
        timeframe_group = self._get_timeframe_group(timeframe)
        return self.data_dir / symbol_dir / timeframe_group / f"{timeframe}.json"

    def _read_from_cache(self, cache_key: tuple) -> Optional[Dict[str, Any]]:
        if cache_key in self.historical_cache:
            logger.info(f"✅ Found historical data for {cache_key} in cache.")
            return self.historical_cache[cache_key]
        return None

    def _read_from_file(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
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
        file_path = self._get_file_path(symbol, timeframe)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved historical data for {symbol} ({timeframe}) to {file_path}")
        except IOError as e:
            logger.error(f"❌ Error saving historical data file {file_path}: {e}")

    def _fetch_from_network(self, symbol: str, timeframe: str, days_to_fetch: int) -> List[List[str]]:
        logger.info(f"📊 Fetching historical data for {symbol} ({timeframe}) for {days_to_fetch} days from network...")
        all_candles = []
        current_before_ts = None
        endpoint_url = f"{self.base_url}/api/v5/market/candles"
        limit_per_request = 300

        tf_minutes = self._timeframe_to_minutes(timeframe)
        total_candles_needed = (days_to_fetch * 24 * 60) / tf_minutes

        while len(all_candles) < total_candles_needed:
            params = {'instId': symbol, 'bar': timeframe, 'limit': str(limit_per_request)}
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
        return self.price_cache.get(symbol)

    def start_data_services(self, symbols: List[str] = None):
        if symbols is None:
            symbols = self.default_symbols
        logger.info("🚀 Starting all data services...")
        self.websocket_client.start(symbols)
        logger.info("✅ WebSocket client started.")

    def stop(self):
        logger.info("⏹️ Stopping data fetcher...")
        self._stop_event.set()
        logger.info("✅ Stop signal sent.")
