import okx.MarketData as MarketData
import pandas as pd
from typing import Dict, List, Optional
import logging
import time
import os
from pathlib import Path

from ..utils.exceptions import DataUnavailableError

logger = logging.getLogger(__name__)

class DataFetcher:
    """
    A class to fetch historical market data from the OKX exchange,
    with an integrated caching mechanism to reduce API calls.
    """
    def __init__(self, config: Dict):
        self.exchange_config = config.get('exchange', {})
        self.cache_config = config.get('cache', {})

        self.debug = self.exchange_config.get('SANDBOX_MODE', True)
        flag = "1" if self.debug else "0"

        self.market_api = MarketData.MarketAPI(
            api_key=self.exchange_config.get('API_KEY'),
            api_secret_key=self.exchange_config.get('API_SECRET'),
            passphrase=self.exchange_config.get('PASSWORD'),
            use_server_time=False,
            flag=flag,
            debug=self.debug
        )

        # Create cache directory if it doesn't exist
        if self.cache_config.get('ENABLED'):
            Path(self.cache_config.get('DIRECTORY', 'data/cache')).mkdir(parents=True, exist_ok=True)

    def _get_cache_filepath(self, symbol: str, timeframe: str, limit: int) -> str:
        """Generates a standardized filepath for a cache file."""
        cache_dir = self.cache_config.get('DIRECTORY', 'data/cache')
        return os.path.join(cache_dir, f"{symbol.replace('/', '_')}_{timeframe}_{limit}.csv")

    def _read_from_cache(self, filepath: str) -> Optional[pd.DataFrame]:
        """Reads data from a cache file if it's valid and not expired."""
        if not os.path.exists(filepath):
            return None

        try:
            file_mod_time = os.path.getmtime(filepath)
            expiration_seconds = self.cache_config.get('EXPIRATION_MINUTES', 15) * 60

            if time.time() - file_mod_time < expiration_seconds:
                logger.info(f"Cache hit. Reading from {filepath}")
                return pd.read_csv(filepath)
            else:
                logger.info(f"Cache expired for {filepath}. Re-fetching.")
                return None
        except Exception as e:
            logger.error(f"Error reading cache file {filepath}: {e}")
            return None

    def _write_to_cache(self, filepath: str, df: pd.DataFrame):
        """Writes a DataFrame to a cache file."""
        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Successfully wrote data to cache file: {filepath}")
        except Exception as e:
            logger.error(f"Error writing to cache file {filepath}: {e}")

    def _fetch_from_api(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """The core logic to fetch data directly from the OKX API."""
        logger.info(f"Fetching {limit} historical data for {symbol} on {timeframe} from API...")

        API_MAX_LIMIT = 100
        all_candles = []
        end_timestamp = ''
        requests_needed = (limit + API_MAX_LIMIT - 1) // API_MAX_LIMIT

        for i in range(requests_needed):
            try:
                result = self.market_api.get_history_candlesticks(
                    instId=symbol, bar=timeframe, limit=str(API_MAX_LIMIT), before=end_timestamp
                )
                if result.get('code') == '0':
                    data = result.get('data', [])
                    if not data:
                        break
                    all_candles.extend(data)
                    end_timestamp = data[-1][0]
                    time.sleep(0.2)
                else:
                    logger.error(f"API Error for {symbol}: {result.get('msg')}")
                    break
            except Exception as e:
                logger.exception(f"Exception during API fetch for {symbol}: {e}")
                break

        if not all_candles:
            return None

        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df['timestamp'] = pd.to_numeric(df['timestamp'])
        df = df.drop_duplicates(subset=['timestamp']).sort_values(by='timestamp', ascending=True)
        return df.tail(limit).reset_index(drop=True)

    def fetch_historical_data(self, symbol: str, timeframe: str, limit: int = 300) -> Dict:
        """
        Fetches historical data, using a cache if available and enabled.

        Raises:
            DataUnavailableError: If data cannot be fetched from the API.
        """
        use_cache = self.cache_config.get('ENABLED')
        cache_filepath = None

        if use_cache:
            cache_filepath = self._get_cache_filepath(symbol, timeframe, limit)
            df = self._read_from_cache(cache_filepath)
            if df is not None:
                return {"symbol": symbol, "data": df.to_dict('records')}

        # Fetch from API if cache is disabled or there was a cache miss
        df = self._fetch_from_api(symbol, timeframe, limit)
        if df is None:
            raise DataUnavailableError(f"Failed to fetch required data for {symbol} on {timeframe}.")

        # Write to cache if enabled and we have a path
        if use_cache and cache_filepath:
            self._write_to_cache(cache_filepath, df)

        return {"symbol": symbol, "data": df.to_dict('records')}


if __name__ == '__main__':
    # Example usage for testing
    from src.config import get_config

    config = get_config()
    fetcher = DataFetcher(config)

    # --- Test fetching BTC data ---
    btc_data = fetcher.fetch_historical_data('BTC-USDT', '1D', limit=500)
    if btc_data:
        print(f"\nSuccessfully fetched BTC-USDT 1D data. Sample:")
        df = pd.DataFrame(btc_data['data'])
        print(df.head())
        print(f"Total rows: {len(df)}")
    else:
        print("\nFailed to fetch BTC-USDT 1D data.")
