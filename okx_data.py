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
from concurrent.futures import ThreadPoolExecutor
from okx_websocket_client import OKXWebSocketClient

# Based on the analysis of logs, some timeframes are not supported for all pairs.
# This list can be expanded or fetched dynamically in a future improvement.
# OKX API uses '1H' for 1-hour, but internal config uses '1h'. The conversion is in main_bot.py.
# This list uses the internal config format.
# Corrected based on user-provided analysis and logs. It seems most major pairs support all timeframes.
# The previous assumption for BTC was incorrect.
SUPPORTED_COMBINATIONS = {
    'BTC-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'ETH-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'SOL-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'XRP-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'DOGE-USDT':  ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'ADA-USDT':   ['1m', '3m', '1h', '2h', '4h', '1d'], # This one seems to have fewer supported timeframes
    'AVAX-USDT':  ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'DOT-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'BNB-USDT':   ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
    'MATIC-USDT': ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'],
}

def validate_symbol_timeframe(symbol: str, timeframe: str):
    """
    Checks if a given symbol/timeframe combination is likely supported.
    Raises ValueError if not found in the supported list.
    The symbol format is 'BTC/USDT'.
    """
    okx_symbol = symbol.replace('/', '-')
    supported_for_symbol = SUPPORTED_COMBINATIONS.get(okx_symbol)

    # If the symbol is not explicitly listed, assume it has the same support as ETH (more comprehensive).
    if not supported_for_symbol:
        supported_for_symbol = SUPPORTED_COMBINATIONS['ETH-USDT']

    if timeframe not in supported_for_symbol:
        raise ValueError(f"Timeframe {timeframe} is not supported for {symbol} on OKX.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('okx_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OKXDataFetcher:
    """
    Fetches historical and REST-based data from OKX.
    Manages the WebSocket client for live data.
    """
    def __init__(self, data_dir: str = 'okx_data'):
        self.base_url = 'https://www.okx.com'
        self.data_dir = Path(data_dir)
        self.price_cache = {}
        self.historical_cache = {}
        self._stop_event = threading.Event()

        self.websocket_client = OKXWebSocketClient(
            price_cache=self.price_cache,
            stop_event=self._stop_event
        )
        self.default_symbols = [
            'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT',
            'ADA-USDT', 'SOL-USDT', 'DOT-USDT', 'DOGE-USDT',
            'MATIC-USDT', 'LTC-USDT', 'LINK-USDT', 'UNI-USDT'
        ]
        self._ensure_data_directory()
        logger.info(f"📁 OKX Data Fetcher initialized - Data Dir: {self.data_dir}")

    def _ensure_data_directory(self):
        try:
            self.data_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"❌ Error creating data directory: {e}")

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

    def fetch_historical_data(self, symbol: str = 'BTC-USDT', timeframe: str = '1D', days_to_fetch: int = 365) -> List[Dict]:
        """
        Fetches historical data, checking cache first.
        This version uses a more robust while loop to ensure all required data is fetched.
        """
        cache_key = (symbol, timeframe, days_to_fetch)
        if cache_key in self.historical_cache:
            logger.info(f"✅ Found historical data for {cache_key} in cache.")
            return self.historical_cache[cache_key]

        try:
            logger.info(f"📊 Fetching historical data for {symbol} ({timeframe}) for {days_to_fetch} days from network...")
            all_candles = []
            current_before_ts = None
            endpoint_url = f"{self.base_url}/api/v5/market/candles"
            # Use the maximum limit allowed by the API to be more efficient
            limit_per_request = 300

            tf_minutes = self._timeframe_to_minutes(timeframe)
            if tf_minutes <= 0: tf_minutes = 1440
            total_candles_needed = (days_to_fetch * 24 * 60) / tf_minutes

            max_requests = 20 # Safety break to prevent infinite loops

            while len(all_candles) < total_candles_needed and max_requests > 0:
                params = {'instId': symbol, 'bar': timeframe, 'limit': str(limit_per_request)}
                if current_before_ts:
                    params['before'] = current_before_ts

                response = requests.get(endpoint_url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                max_requests -= 1

                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '0':
                        candles_data = data.get('data', [])
                        if not candles_data:
                            logger.info(f"⏹️ No more historical data returned from API for {symbol}. Fetched {len(all_candles)} candles.")
                            break

                        all_candles.extend(candles_data)
                        current_before_ts = candles_data[-1][0]
                        time.sleep(0.3) # Respect rate limits
                    else:
                        raise Exception(f"API Error: {data.get('msg', 'Unknown error')}")
                else:
                    raise Exception(f"HTTP Error: {response.status_code} - {response.text}")

            if max_requests == 0:
                logger.warning(f"⚠️ Hit max request limit for {symbol}. The data might be incomplete.")

            historical_data = []
            seen_timestamps = set()
            for candle in all_candles:
                timestamp = int(candle[0])
                if timestamp not in seen_timestamps:
                    historical_data.append({
                        'timestamp': timestamp, 'open': float(candle[1]), 'high': float(candle[2]),
                        'low': float(candle[3]), 'close': float(candle[4]), 'volume': float(candle[5]),
                        'date': datetime.fromtimestamp(timestamp / 1000).isoformat()
                    })
                    seen_timestamps.add(timestamp)

            historical_data.sort(key=lambda x: x['timestamp'])
            self.historical_cache[cache_key] = historical_data
            logger.info(f"✅ Fetched and cached {len(historical_data)} unique candles for {symbol}")
            return historical_data
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
            return []

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
