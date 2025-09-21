import okx.MarketData as MarketData
import pandas as pd
from typing import Dict, List, Optional
import logging

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
        Fetches historical candlestick data for a given symbol and timeframe.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC-USDT').
            timeframe (str): The timeframe for the candles (e.g., '1D', '4H', '15m').
            limit (int): The number of candles to fetch. Max is 300 for historical.

        Returns:
            Optional[Dict]: A dictionary containing the data, or None if an error occurs.
        """
        logger.info(f"Fetching historical data for {symbol} on {timeframe} timeframe...")
        try:
            result = self.market_api.get_history_candlesticks(
                instId=symbol,
                bar=timeframe,
                limit=str(limit)
            )

            if result.get('code') == '0':
                data = result.get('data', [])
                if not data:
                    logger.warning(f"No data returned for {symbol} on {timeframe}.")
                    return None

                # Convert to DataFrame for easier use later
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
                df['timestamp'] = pd.to_numeric(df['timestamp'])
                # Sort by timestamp ascending, as OKX returns descending
                df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)

                logger.info(f"Successfully fetched {len(df)} candles for {symbol} on {timeframe}.")
                return {"symbol": symbol, "data": df.to_dict('records')}
            else:
                logger.error(f"Error fetching data for {symbol}: {result.get('msg')}")
                return None
        except Exception as e:
            logger.exception(f"An exception occurred while fetching data for {symbol}: {e}")
            return None

if __name__ == '__main__':
    # Example usage for testing
    from src.config import get_config

    config = get_config()
    fetcher = DataFetcher(config)

    # --- Test fetching BTC data ---
    btc_data = fetcher.fetch_historical_data('BTC-USDT', '1D')
    if btc_data:
        print(f"\nSuccessfully fetched BTC-USDT 1D data. Sample:")
        df = pd.DataFrame(btc_data['data'])
        print(df.head())
    else:
        print("\nFailed to fetch BTC-USDT 1D data.")

    # --- Test fetching a non-existent symbol ---
    fake_data = fetcher.fetch_historical_data('FAKE-COIN-USDT', '1H')
    if not fake_data:
        print("\nCorrectly handled non-existent symbol.")
