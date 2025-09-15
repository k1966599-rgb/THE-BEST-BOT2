import asyncio
import json
import threading
import time
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.data_retrieval.okx_fetcher import OKXDataFetcher
from src.config import get_config

class TestWebSocketShutdown(unittest.TestCase):
    def test_websocket_graceful_shutdown(self):
        """
        Verify that the WebSocket client thread shuts down gracefully.
        """
        config = get_config()
        fetcher = OKXDataFetcher(config)

        # We use a real thread, but we mock the websocket connection
        # to avoid network calls and to control the behavior.
        async def mock_recv():
            await asyncio.sleep(0.1) # Simulate work
            return json.dumps({"data": [{"instId": "BTC-USDT", "last": "50000"}]})

        mock_websocket = AsyncMock()
        mock_websocket.recv.side_effect = mock_recv
        mock_websocket.send.return_value = None
        mock_websocket.close.return_value = None

        # The context manager should return our mock
        mock_connect = patch('websockets.connect', new_callable=AsyncMock)
        mock_connect_instance = mock_connect.start()
        mock_connect_instance.return_value.__aenter__.return_value = mock_websocket

        # Start the services
        fetcher.start_data_services(['BTC-USDT'])
        time.sleep(0.5) # Give the thread time to start and connect

        # Check that the thread is alive
        ws_thread = fetcher.websocket_client.ws_thread
        self.assertTrue(ws_thread.is_alive())

        # Stop the services
        fetcher.stop()

        # The thread should terminate now. We give it a timeout.
        ws_thread.join(timeout=5)
        self.assertFalse(ws_thread.is_alive())

        mock_connect.stop()

if __name__ == '__main__':
    unittest.main()
