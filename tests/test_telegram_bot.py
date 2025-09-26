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
    },
    # Add the UI config part that setup_conversation_handler needs, as it's
    # now created dynamically.
    'ui': {
        'CALLBACK_DATA': {
            'analyze_start': 'analyze_start',
            'bot_status': 'bot_status',
            'main_menu': 'main_menu',
            'symbol_prefix': 'symbol_',
            'term_prefix': 'term_',
            'timeframe_prefix': 'timeframe_',
        }
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
        # Import the setup function and necessary components from the bot module
        from telegram_bot import setup_conversation_handler, select_term, TIMEFRAME

        # Create the handler instance for testing, reflecting the new architecture
        self.conv_handler = setup_conversation_handler(mock_config)
        self.select_term = select_term
        self.TIMEFRAME = TIMEFRAME

    def test_back_button_handler_is_present_in_timeframe_state(self, mock_get_config, mock_fetcher, mock_analyzer):
        """
        Verifies that the TIMEFRAME state has a handler for the 'Back' button.
        This test will fail if the handler is removed or its pattern changes.
        """
        timeframe_state_handlers = self.conv_handler.states.get(self.TIMEFRAME, [])

        # The 'Back' button from the timeframe selection should trigger a handler
        # with a pattern that matches a symbol (e.g., 'symbol_BTC/USDT').
        has_back_button_handler = any(
            hasattr(handler, 'pattern') and handler.pattern.match('symbol_BTC/USDT')
            for handler in timeframe_state_handlers
        )

        self.assertTrue(
            has_back_button_handler,
            "The ConversationHandler's TIMEFRAME state is missing a handler "
            "for the 'symbol_' pattern, which is required for the 'Back' button to work."
        )

        # Find the specific handler to verify its callback function.
        back_handler = next(
            (h for h in timeframe_state_handlers if hasattr(h, 'pattern') and h.pattern.match('symbol_BTC/USDT')),
            None
        )
        self.assertIsNotNone(back_handler, "The handler for the 'symbol_' pattern was not found.")

        # Verify that this handler correctly points to the `select_term` function
        self.assertEqual(
            back_handler.callback,
            self.select_term,
            "The 'Back' button's handler should call the `select_term` function."
        )

if __name__ == '__main__':
    unittest.main()