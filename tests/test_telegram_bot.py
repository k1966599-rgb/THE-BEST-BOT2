import unittest
from unittest.mock import patch

# Mock the configuration before importing the bot module. This prevents errors
# related to missing config files or environment variables during testing.
mock_config = {
    'trading': {
        'WATCHLIST': ['BTC/USDT', 'ETH/USDT'],
        'TIMEFRAME_GROUPS': {
            'long_term': ['1d', '4h'],
            'medium_term': ['1h', '30m'],
            'short_term': ['15m', '5m']
        }
    },
    'telegram': {
        'TOKEN': 'mock-token-for-testing'
    }
}

# The class decorators patch dependencies. The mocks are passed to each test
# method in reverse order of the decorator stack (from bottom to top).
@patch('src.strategies.fibo_analyzer.FiboAnalyzer')
@patch('src.data_retrieval.data_fetcher.DataFetcher')
@patch('src.config.get_config', return_value=mock_config)
class TestTelegramBotConversation(unittest.TestCase):

    def setUp(self):
        """Load the bot's components. This runs before each test."""
        from src.telegram_bot import conv_handler, select_term, TIMEFRAME
        self.conv_handler = conv_handler
        self.select_term = select_term
        self.TIMEFRAME = TIMEFRAME

    def test_back_button_handler_is_present_in_timeframe_state(self, mock_get_config, mock_fetcher, mock_analyzer):
        """
        Verifies that the TIMEFRAME state has a handler for the 'Back' button.
        This test will fail before the fix and pass after it.
        """
        timeframe_state_handlers = self.conv_handler.states.get(self.TIMEFRAME, [])

        has_back_button_handler = any(
            hasattr(handler, 'pattern') and handler.pattern.match('symbol_BTC/USDT')
            for handler in timeframe_state_handlers
        )

        # This assertion will fail before the fix.
        self.assertTrue(
            has_back_button_handler,
            "BUG: The ConversationHandler's TIMEFRAME state is missing a handler "
            "for the 'symbol_' pattern, breaking the 'Back' button."
        )

        # Find the specific handler to verify its callback function.
        back_handler = next(
            (h for h in timeframe_state_handlers if hasattr(h, 'pattern') and h.pattern.match('symbol_BTC/USDT')),
            None
        )
        self.assertIsNotNone(back_handler, "The handler for the 'symbol_' pattern was not found.")
        self.assertEqual(
            back_handler.callback,
            self.select_term,
            "The 'Back' button's handler should call the `select_term` function."
        )

if __name__ == '__main__':
    unittest.main()