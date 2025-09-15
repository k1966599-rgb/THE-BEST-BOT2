import asyncio
import websockets
import json
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OKXWebSocketClient:
    """Manages the WebSocket connection for real-time OKX ticker data.

    This class handles connecting to the OKX WebSocket, subscribing to ticker
    channels, processing incoming data, and managing automatic reconnections
    in case of failures.
    """
    def __init__(self, config: Dict, price_cache: Dict):
        """Initializes the OKXWebSocketClient.

        Args:
            config (Dict): The main configuration dictionary.
            price_cache (Dict): A dictionary shared with the data fetcher to
                store the latest price data.
        """
        self.config = config
        self.ws_url = 'wss://ws.okx.com:8443/ws/v5/public'
        self.price_cache = price_cache
        self._stop_event = threading.Event()
        self.is_connected = False
        self.reconnect_interval = 5
        self.ws_connection = None
        self.ws_thread = None

    async def _start_websocket(self, symbols: List[str] = None):
        """Starts and manages the WebSocket connection loop.

        This coroutine handles the entire lifecycle of the WebSocket connection,
        including initial connection, subscription, message handling, and
        automatic reconnection on failure.

        Args:
            symbols (List[str]): A list of symbols to subscribe to.
        """
        if not symbols:
            logger.warning("No symbols provided to WebSocket client. It will not subscribe to any channels.")
            return

        while not self._stop_event.is_set():
            try:
                logger.info("🔗 Attempting to connect to WebSocket...")
                async with websockets.connect(self.ws_url) as websocket:
                    self.ws_connection = websocket
                    self.is_connected = True
                    logger.info("✅ WebSocket connected")

                    subscribe_message = {
                        "op": "subscribe",
                        "args": [{"channel": "tickers", "instId": symbol} for symbol in symbols]
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    logger.info(f"📡 Subscribed to {len(symbols)} symbols")

                    while not self._stop_event.is_set():
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            data = json.loads(message)
                            if 'data' in data and data.get('data'):
                                await self._process_websocket_data(data['data'])
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("WebSocket connection closed. Reconnecting...")
                            break
                        except Exception as e:
                            logger.error(f"❌ Error processing WebSocket message: {e}")
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")
            finally:
                self.is_connected = False
                if not self._stop_event.is_set():
                    logger.info(f"⏳ Reconnecting in {self.reconnect_interval} seconds...")
                    for _ in range(self.reconnect_interval):
                        if self._stop_event.is_set():
                            break
                        await asyncio.sleep(1)

    async def _process_websocket_data(self, data_list: List[Dict]):
        """Processes incoming WebSocket data and updates the price cache.

        Args:
            data_list (List[Dict]): A list of ticker data dictionaries received
                from the WebSocket.
        """
        try:
            for ticker in data_list:
                price_data = {
                    'symbol': ticker['instId'],
                    'price': float(ticker['last']),
                    'change_24h': float(ticker.get('chg24h', 0)),
                    'change_percent': float(ticker.get('chgPct24h', 0)),
                    'high_24h': float(ticker.get('high24h', 0)),
                    'low_24h': float(ticker.get('low24h', 0)),
                    'volume': float(ticker.get('vol24h', 0)),
                    'timestamp': int(ticker.get('ts', 0)),
                    'last_update': datetime.now().isoformat()
                }
                self.price_cache[ticker['instId']] = price_data
        except Exception as e:
            logger.error(f"❌ Error processing WebSocket data: {e}")

    def start(self, symbols: List[str] = None):
        """Starts the WebSocket client in a separate background thread.

        This method creates and starts a new daemon thread that runs the
        asyncio event loop for the WebSocket connection, allowing it to
        operate in the background without blocking the main application.

        Args:
            symbols (List[str], optional): A list of symbols to subscribe to.
                If None, uses default symbols. Defaults to None.
        """
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_websocket(symbols))

        self.ws_thread = threading.Thread(target=run_loop, daemon=True)
        self.ws_thread.start()
        logger.info("✅ WebSocket client thread started.")

    def stop(self):
        """Stops the WebSocket client thread."""
        logger.info("⏹️ Stopping WebSocket client...")
        self._stop_event.set()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join()
        logger.info("✅ WebSocket client stopped.")
