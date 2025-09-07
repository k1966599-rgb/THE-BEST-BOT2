import asyncio
import websockets
import json
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OKXWebSocketClient:
    def __init__(self, price_cache: Dict, stop_event: threading.Event):
        self.ws_url = 'wss://ws.okx.com:8443/ws/v5/public'
        self.price_cache = price_cache
        self._stop_event = stop_event
        self.is_connected = False
        self.reconnect_interval = 5
        self.ws_connection = None
        self.default_symbols = [
            'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT',
            'ADA-USDT', 'SOL-USDT', 'DOT-USDT', 'DOGE-USDT',
            'MATIC-USDT', 'LTC-USDT', 'LINK-USDT', 'UNI-USDT'
        ]

    async def _start_websocket(self, symbols: List[str] = None):
        """Starts the WebSocket connection for live data."""
        if symbols is None:
            symbols = self.default_symbols

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
                    await asyncio.sleep(self.reconnect_interval)

    async def _process_websocket_data(self, data_list: List[Dict]):
        """Processes incoming WebSocket data and updates the shared price cache."""
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
        """Starts the WebSocket client in a new thread."""
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_websocket(symbols))

        ws_thread = threading.Thread(target=run_loop, daemon=True)
        ws_thread.start()
        logger.info("✅ WebSocket client thread started.")
