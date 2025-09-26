import okx.MarketData as MarketData
import pandas as pd
from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)

class DataFetcher:
    """
    A class to fetch historical market data from the OKX exchange.
    """
    def __init__(self, config: Dict):
        self.config = config.get('exchange', {})
        self.debug = self.config.get('SANDBOX_MODE', True)
        flag = "1" if self.debug else "0"  # 0 for live, 1 for demo

        self.market_api = MarketData.MarketAPI(
            api_key=self.config.get('API_KEY'),
            api_secret_key=self.config.get('API_SECRET'),
            passphrase=self.config.get('PASSWORD'),
            use_server_time=False,
            flag=flag,
            debug=self.debug
        )

    def fetch_historical_data(self, symbol: str, timeframe: str, limit: int = 300) -> Optional[Dict]:
        """
        Fetches historical candlestick data for a given symbol and timeframe,
        handling pagination to retrieve large datasets.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC-USDT').
            timeframe (str): The timeframe for the candles (e.g., '1D', '4H', '15m').
            limit (int): The total number of candles to fetch.

        Returns:
            Optional[Dict]: A dictionary containing the data, or None if an error occurs.
        """
        logger.info(f"Fetching {limit} historical data for {symbol} on {timeframe} timeframe...")

        API_MAX_LIMIT = 100  # OKX API limit for historical candles
        all_candles = []
        end_timestamp = '' # Start with no end time

        requests_needed = (limit + API_MAX_LIMIT - 1) // API_MAX_LIMIT
        logger.info(f"Need to make {requests_needed} API requests.")

        for i in range(requests_needed):
            try:
                logger.info(f"Fetching page {i+1}/{requests_needed} for {symbol}...")

                result = self.market_api.get_history_candlesticks(
                    instId=symbol,
                    bar=timeframe,
                    limit=str(API_MAX_LIMIT),
                    before=end_timestamp
                )

                if result.get('code') == '0':
                    data = result.get('data', [])
                    if not data:
                        logger.warning(f"No more data returned for {symbol}. Fetched {len(all_candles)} candles in total.")
                        break

                    # The first element is the newest, last is the oldest.
                    # We add all but the first one to avoid duplicates if the range overlaps.
                    all_candles.extend(data)

                    # The timestamp of the oldest candle becomes the 'before' for the next request
                    end_timestamp = data[-1][0]

                    # Respect API rate limits
                    time.sleep(0.2) # 200ms delay between requests

                else:
                    logger.error(f"Error fetching page {i+1} for {symbol}: {result.get('msg')}")
                    # Don't stop, just return what we have so far
                    break

            except Exception as e:
                logger.exception(f"An exception occurred while fetching page {i+1} for {symbol}: {e}")
                break

        if not all_candles:
            logger.error(f"Failed to fetch any data for {symbol}.")
            return None

        # Convert to DataFrame for easier use later
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df['timestamp'] = pd.to_numeric(df['timestamp'])

        # Remove duplicates that might occur at page boundaries and sort
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)

        # Trim the data to the exact limit requested
        if len(df) > limit:
            df = df.tail(limit)

        logger.info(f"Successfully fetched a total of {len(df)} candles for {symbol} on {timeframe}.")
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
