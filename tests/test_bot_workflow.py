import pytest
from unittest.mock import MagicMock, AsyncMock
import pandas as pd
import anyio

from src.config import get_config
from src.analysis.data_models import Level
from src.decision_engine.trade_setup import TradeSetup
from src.notifiers.telegram_notifier import InteractiveTelegramBot
from src.data_retrieval.okx_fetcher import OKXDataFetcher

@pytest.fixture
def mock_fetcher():
    fetcher = MagicMock()
    fetcher.fetch_historical_data = AsyncMock(return_value={
        'data': [{'close': 100, 'high': 110, 'low': 90, 'timestamp': 12345}]
    })
    fetcher.get_cached_price.return_value = {'price': 100}
    return fetcher

@pytest.fixture
def core_components(mock_fetcher):
    """Initializes and provides all core components needed for the test."""
    config = get_config()

    # We don't need a real orchestrator or decision engine for this test,
    # as we are mocking the bot's internal methods.

    yield config, mock_fetcher

@pytest.mark.anyio
async def test_bot_full_analysis_workflow(core_components):
    """
    Tests the entire analysis and reporting workflow as triggered by the bot.
    """
    config, fetcher = core_components

    bot = InteractiveTelegramBot(
        config=config,
        fetcher=fetcher
    )

    # Mock the internal analysis method to avoid running the full analysis pipeline
    bot._run_analysis_for_request = AsyncMock(return_value=(
        [
            {'type': 'header', 'content': '...'},
            {'type': 'timeframe', 'content': '...'},
            {'type': 'final_summary', 'content': '...', 'keyboard': 'follow_ignore'}
        ],
        [{'trade_setup': True}] # Dummy ranked recs
    ))

    symbol = 'BTC/USDT'
    timeframes = get_config()['trading']['TIMEFRAME_GROUPS']['long_term']
    analysis_type = "long_term"
    chat_id = 12345

    # --- Execute ---
    report_messages, ranked_recs = await bot._run_analysis_for_request(chat_id, symbol, timeframes, analysis_type)

    # --- Verify ---
    assert isinstance(report_messages, list)
    assert len(report_messages) > 0
    assert ranked_recs is not None
