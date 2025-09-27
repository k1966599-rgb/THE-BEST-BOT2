import asyncio
import json
import hmac
import base64
from datetime import datetime
import logging

import websockets

logger = logging.getLogger(__name__)

class OKXWebSocketClient:
    """
    Handles the connection to the OKX WebSocket API for real-time data.
    """
    def __init__(self, api_key: str, api_secret: str, passphrase: str, watchlist: list, on_message_callback=None, sandbox_mode=True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.watchlist = watchlist
        self.on_message_callback = on_message_callback

        self.ws_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999" if sandbox_mode else "wss://ws.okx.com:8443/ws/v5/private"

    def _get_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Generates the signature required for authentication."""
        message = f"{timestamp}{method}{request_path}{body}"
        mac = hmac.new(bytes(self.api_secret, 'utf-8'), bytes(message, 'utf-8'), digestmod='sha256')
        return base64.b64encode(mac.digest()).decode()

    async def _login(self, ws):
        """Sends the login message to the WebSocket."""
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        signature = self._get_signature(timestamp, "GET", "/users/self/verify")

        login_payload = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": signature
            }]
        }
        await ws.send(json.dumps(login_payload))
        logger.info("Sent login request to OKX WebSocket.")

    async def _subscribe_to_tickers(self, ws):
        """Subscribes to the ticker channels for the watchlist."""
        args = [{"channel": "tickers", "instId": symbol} for symbol in self.watchlist]
        subscribe_payload = {
            "op": "subscribe",
            "args": args
        }
        await ws.send(json.dumps(subscribe_payload))
        logger.info(f"Subscribed to ticker channels for: {self.watchlist}")

    async def listen(self):
        """The main loop that connects, authenticates, and listens for messages."""
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    await self._login(ws)

                    # Wait for login confirmation
                    login_response = await ws.recv()
                    login_data = json.loads(login_response)
                    if login_data.get("event") == "login" and login_data.get("code") == "0":
                        logger.info("Successfully logged into OKX WebSocket.")
                        await self._subscribe_to_tickers(ws)
                    else:
                        logger.error(f"WebSocket login failed: {login_data.get('msg')}")
                        break

                    # Listen for messages
                    while True:
                        message = await ws.recv()
                        data = json.loads(message)

                        if "event" in data:
                            if data["event"] == "error":
                                logger.error(f"WebSocket error: {data.get('msg')}")
                            elif data["event"] == "subscribe":
                                logger.info(f"Subscription confirmation for: {data['arg']['channel']}")
                            continue

                        # Process ticker data
                        if "arg" in data and data["arg"]["channel"] == "tickers":
                            if self.on_message_callback:
                                for ticker_data in data.get('data', []):
                                    await self.on_message_callback(ticker_data)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"An unexpected error occurred in WebSocket client: {e}", exc_info=True)
                logger.warning("Reconnecting in 10 seconds...")
                await asyncio.sleep(10)