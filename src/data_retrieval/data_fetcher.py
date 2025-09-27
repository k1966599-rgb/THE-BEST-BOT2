import okx.MarketData as MarketData
import okx.Account as Account
import pandas as pd
from typing import Dict, List, Optional
import logging
import time
from requests.exceptions import RequestException

from .exceptions import APIError, NetworkError

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

        self.account_api = Account.AccountAPI(
            api_key=self.config.get('API_KEY'),
            api_secret_key=self.config.get('API_SECRET'),
            passphrase=self.config.get('PASSWORD'),
            use_server_time=False,
            flag=flag,
            debug=self.debug
        )

    def get_account_balance(self) -> Dict:
        """
        Fetches the account balance, filtering for non-zero assets.

        Returns:
            Dict: A dictionary containing a list of balance details.

        Raises:
            APIError: If the exchange API returns an error.
            NetworkError: If a network-related error occurs.
        """
        logger.info("Fetching account balance...")
        try:
            result = self.account_api.get_account_balance()
        except RequestException as e:
            logger.error(f"Network error while fetching account balance: {e}")
            raise NetworkError(f"Failed to connect to the exchange: {e}") from e

        if result.get('code') != '0':
            error_msg = result.get('msg', 'Unknown API error')
            error_code = result.get('code')
            logger.error(f"API Error fetching balance: {error_msg} (Code: {error_code})")
            raise APIError(error_msg, status_code=error_code)

        all_details = result.get('data', [{}])[0].get('details', [])

        # Filter for assets where there is an available or frozen balance
        non_zero_balances = [
            detail for detail in all_details
            if float(detail.get('availBal', 0)) > 0 or float(detail.get('frozenBal', 0)) > 0
        ]

        logger.info(f"Successfully fetched and filtered balances. Found {len(non_zero_balances)} non-zero assets.")
        return {"data": non_zero_balances}

    def get_positions(self) -> Dict:
        """
        Fetches open positions for the account (specifically for SWAP instruments).

        Returns:
            Dict: A dictionary containing a list of open positions.

        Raises:
            APIError: If the exchange API returns an error.
            NetworkError: If a network-related error occurs.
        """
        logger.info("Fetching open positions...")
        try:
            # We specify SWAP as the instrument type, which is common for futures trading.
            result = self.account_api.get_positions(instType='SWAP')
        except RequestException as e:
            logger.error(f"Network error while fetching positions: {e}")
            raise NetworkError(f"Failed to connect to the exchange: {e}") from e

        if result.get('code') != '0':
            error_msg = result.get('msg', 'Unknown API error')
            error_code = result.get('code')
            logger.error(f"API Error fetching positions: {error_msg} (Code: {error_code})")
            raise APIError(error_msg, status_code=error_code)

        positions = result.get('data', [])

        # The API returns all positions, even those with 0 size. We filter for open ones.
        open_positions = [
            pos for pos in positions
            if float(pos.get('pos', 0)) != 0
        ]

        logger.info(f"Successfully fetched positions. Found {len(open_positions)} open positions.")
        return {"data": open_positions}

    def fetch_historical_data(self, symbol: str, timeframe: str, limit: int = 300) -> Dict:
        """
        Fetches historical candlestick data for a given symbol and timeframe.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC-USDT').
            timeframe (str): The timeframe for the candles (e.g., '1D', '4H', '15m').
            limit (int): The total number of candles to fetch.

        Returns:
            Dict: A dictionary containing the data.

        Raises:
            APIError: If the exchange API returns an error.
            NetworkError: If a network-related error occurs.
        """
        logger.info(f"Fetching {limit} historical data for {symbol} on {timeframe} timeframe...")

        API_MAX_LIMIT = 100
        all_candles = []
        end_timestamp = ''

        logger.info(f"Starting paginated data fetch for {symbol} to get {limit} candles...")

        while len(all_candles) < limit:
            try:
                # Always fetch the max allowed per request to be efficient
                logger.info(f"Requesting batch of up to {API_MAX_LIMIT}. Have {len(all_candles)}/{limit} candles.")
                result = self.market_api.get_history_candlesticks(
                    instId=symbol, bar=timeframe, limit=str(API_MAX_LIMIT), before=end_timestamp
                )
            except RequestException as e:
                logger.error(f"Network error while fetching {symbol}: {e}")
                raise NetworkError(f"Failed to connect to the exchange: {e}") from e
            except Exception as e:
                logger.exception(f"An unexpected error occurred during API call for {symbol}: {e}")
                raise

            if result.get('code') != '0':
                error_msg = result.get('msg', 'Unknown API error')
                error_code = result.get('code')
                logger.error(f"API Error for {symbol}: {error_msg} (Code: {error_code})")
                # Specific check for invalid instrument ID
                if error_code == '51001':
                     raise APIError(f"Invalid instrument ID: {symbol}", status_code=error_code)
                raise APIError(error_msg, status_code=error_code)

            data = result.get('data', [])
            if not data:
                logger.warning(f"No more data returned from API for {symbol}. Fetched {len(all_candles)} candles.")
                break # Exit loop if API returns no more data

            all_candles.extend(data)
            end_timestamp = data[-1][0] # Timestamp of the last candle for the next 'before' request
            time.sleep(0.2) # Small delay to respect API rate limits

        if not all_candles:
            raise APIError(f"Failed to fetch any data for {symbol}, it might be an invalid symbol or have no trading history.")

        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df['timestamp'] = pd.to_numeric(df['timestamp'])
        df = df.drop_duplicates(subset=['timestamp']).sort_values(by='timestamp', ascending=True).reset_index(drop=True)

        if len(df) > limit:
            df = df.tail(limit)

        logger.info(f"Successfully fetched a total of {len(df)} candles for {symbol} on {timeframe}.")
        return {"symbol": symbol, "data": df.to_dict('records')}


if __name__ == '__main__':
    from src.config import get_config

    config = get_config()
    fetcher = DataFetcher(config)

    try:
        btc_data = fetcher.fetch_historical_data('BTC-USDT', '1D', limit=500)
        if btc_data:
            print(f"\nSuccessfully fetched BTC-USDT 1D data. Sample:")
            df = pd.DataFrame(btc_data['data'])
            print(df.head())
            print(f"Total rows: {len(df)}")
    except (APIError, NetworkError) as e:
        print(f"\nFailed to fetch data: {e}")

    try:
        # Test invalid symbol
        invalid_data = fetcher.fetch_historical_data('INVALID-SYMBOL', '1D')
    except APIError as e:
        print(f"\nCaught expected error for invalid symbol: {e}")