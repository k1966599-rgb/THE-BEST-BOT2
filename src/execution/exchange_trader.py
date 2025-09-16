import okx.Trade as Trade
import okx.Account as Account
import logging
from typing import Dict, Optional, Any


logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for API authentication errors."""
    pass


class ExchangeTrader:
    """
    Handles order execution and position checking on the OKX exchange.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the ExchangeTrader.

        Args:
            config (Dict[str, Any]): The main configuration dictionary.
        """
        self.config = config.get('exchange', {})
        self.debug = self.config.get('SANDBOX_MODE', True)
        flag = "1" if self.debug else "0"  # 0 for live, 1 for demo

        api_key = self.config.get('API_KEY')
        api_secret = self.config.get('API_SECRET')
        password = self.config.get('PASSWORD')

        # When initializing the APIs, it's crucial to use keyword arguments for clarity
        # and to avoid position-related errors, especially for the 'debug' flag.
        self.trade_api = Trade.TradeAPI(
            api_key=api_key,
            api_secret_key=api_secret,
            passphrase=password,
            use_server_time=False,
            flag=flag,
            debug=self.debug
        )
        self.account_api = Account.AccountAPI(
            api_key=api_key,
            api_secret_key=api_secret,
            passphrase=password,
            use_server_time=False,
            flag=flag,
            debug=self.debug
        )


    def place_order(self, symbol: str, side: str, order_type: str, amount: str, price: Optional[str] = None, sl_tp: Optional[Dict[str, float]] = None) -> Optional[Dict]:
        """
        Places a trade order on the exchange, with optional stop-loss and take-profit.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC-USDT').
            side (str): 'buy' or 'sell'.
            order_type (str): 'market' or 'limit'.
            amount (str): The quantity to buy or sell.
            price (Optional[str]): The price for a limit order.
            sl_tp (Optional[Dict[str, float]]): Dict with 'stop_loss' and 'take_profit' prices.

        Returns:
            Optional[Dict]: A dictionary containing the order ID and other details, or None if it fails.
        """
        logger.info(f"Placing {side} {order_type} order for {amount} of {symbol}...")
        if sl_tp:
            logger.info(f"With Stop-Loss: {sl_tp.get('stop_loss')} and Take-Profit: {sl_tp.get('take_profit')}")

        order_params = {
            'instId': symbol,
            'tdMode': 'cash',
            'side': side,
            'ordType': order_type,
            'sz': amount,
            'px': price
        }

        if sl_tp:
            order_params['slTriggerPx'] = str(sl_tp.get('stop_loss'))
            order_params['tpTriggerPx'] = str(sl_tp.get('take_profit'))
            order_params['slOrdPx'] = '-1' # Indicates a market order for SL
            order_params['tpOrdPx'] = '-1' # Indicates a market order for TP

        try:
            result = self.trade_api.place_order(**order_params)

            if result.get('code') == '0' and result.get('data'):
                order_details = result['data'][0]
                if order_details.get('sCode') == '0':
                    order_id = order_details.get('ordId')
                    logger.info(f"Successfully placed order with ID: {order_id}")
                    return order_details
                else:
                    error_msg = order_details.get('sMsg', 'No error message from exchange.')
                    logger.error(f"Failed to place order. Exchange error: {error_msg} (Code: {order_details.get('sCode')})")
                    return None
            else:
                logger.error(f"Failed to place order. API error: {result.get('msg', 'No error message from API.')}")
                return None
        except Exception as e:
            logger.exception(f"An exception occurred while placing order for {symbol}: {e}")
            return None

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Retrieves the current position for a given symbol.

        Args:
            symbol (str): The instrument ID (e.g., 'BTC-USDT').

        Returns:
            Optional[Dict]: A dictionary with position details if a position exists,
                            otherwise None.

        Raises:
            AuthenticationError: If the API keys are invalid.
        """
        logger.debug(f"Checking for open position in {symbol}...")
        try:
            # For SPOT trading, we check the account balance for the base currency.
            # For MARGIN/FUTURES, we would use get_positions. This is a simplification.
            # We will use the 'positions' endpoint as it's more direct for derivatives.
            result = self.account_api.get_positions(instId=symbol)

            if result.get('code') == '0':
                positions = result.get('data', [])
                if positions:
                    # Assuming we are not in hedging mode and only have one position per symbol
                    position_details = positions[0]
                    # Check if position size is non-zero
                    if float(position_details.get('pos', '0')) != 0:
                        logger.info(f"Found active position for {symbol}: {position_details}")
                        return position_details
                logger.info(f"No active position found for {symbol}.")
                return None
            else:
                error_msg = result.get('msg', '')
                logger.error(f"Error fetching position for {symbol}: {error_msg}")
                # Specific check for authentication failure
                if "invalid" in error_msg.lower() and "key" in error_msg.lower():
                    raise AuthenticationError(error_msg)
                return None
        except AuthenticationError:
            # Re-raise the caught authentication error to be handled by the engine
            raise
        except Exception as e:
            logger.exception(f"An exception occurred while fetching position for {symbol}: {e}")
            return None


if __name__ == '__main__':
    from src.config import get_config

    # Configure basic logging for standalone testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    main_config = get_config()

    if not all([main_config['exchange']['API_KEY'], main_config['exchange']['API_SECRET'], main_config['exchange']['PASSWORD']]):
        logger.warning("API keys are not set in the .env file. Cannot run execution test.")
    else:
        trader = ExchangeTrader(main_config)

        if trader.debug:
            print("\n--- Running Trade Execution Test in SANDBOX Mode ---")

            # We will place a LIMIT order far away from the current market price to avoid execution.
            # This tests connectivity and API key validity without risking funds.
            test_symbol = 'BTC-USDT'
            test_amount = '0.001'  # Amount of BTC to buy
            test_price = '10000.0' # A price that is very unlikely to be filled

            logger.info(f"Attempting to place a LIMIT BUY order for {test_amount} {test_symbol} at a price of {test_price}.")
            order_result = trader.place_order(
                symbol=test_symbol,
                side='buy',
                order_type='limit',
                amount=test_amount,
                price=test_price
            )

            if order_result:
                logger.info(f"Successfully sent test order to the exchange. Response: {order_result}")
            else:
                logger.error("Failed to place test order. Please check your API key permissions and sandbox account status.")
        else:
            logger.warning("--- Skipping trade execution test in LIVE mode for safety. ---")
