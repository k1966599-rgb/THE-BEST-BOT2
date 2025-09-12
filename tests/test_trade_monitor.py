import sys
import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.monitoring.trade_monitor import TradeMonitor
from src.analysis.orchestrator import AnalysisOrchestrator
from src.config import get_config
from src.analysis.data_models import Level, Pattern
from src.decision_engine.trade_setup import TradeSetup

@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send = MagicMock()
    return notifier

@pytest.fixture
def mock_fetcher():
    fetcher = MagicMock()
    # Mock the synchronous fetch_historical_data method
    fetcher.fetch_historical_data.return_value = {
        'data': [{'timestamp': 1, 'open': 50000, 'high': 51000, 'low': 49000, 'close': 50500, 'volume': 100}]
    }
    return fetcher

@pytest.fixture
def mock_orchestrator():
    return MagicMock()

@pytest.fixture
def trade_monitor(mock_fetcher, mock_orchestrator, mock_notifier):
    config = get_config()
    return TradeMonitor(config, mock_fetcher, mock_orchestrator, mock_notifier)

@pytest.fixture
def sample_recommendation():
    """A sample recommendation object to add to the monitor."""
    pattern = Pattern(
        name='Bull Flag',
        status='Forming',
        timeframe='1h',
        activation_level=60000,
        invalidation_level=58000,
        target1=62000
    )
    return {
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'trade_setup': TradeSetup(
            chat_id=123,
            symbol='BTC/USDT',
            timeframe='1h',
            pattern_name='Bull Flag',
            pattern_status='Forming',
            entry_price=60000,
            stop_loss=58000,
            target1=62000,
            raw_pattern_data=pattern.__dict__ # Fix: Pass raw pattern data to the setup
        ),
        'raw_analysis': {
            'supports': [Level(name='Support', value=58000, level_type='support')],
            'resistances': [Level(name='Resistance', value=60000, level_type='resistance')],
            'patterns': [pattern]
        }
    }

def test_add_trade(trade_monitor, sample_recommendation):
    # Act
    trade_monitor.add_trade(sample_recommendation)

    # Assert
    key = "123_BTC/USDT_1h"
    assert key in trade_monitor.followed_trades
    assert trade_monitor.followed_trades[key]['symbol'] == 'BTC/USDT'

@pytest.mark.anyio
async def test_resistance_break_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    # Arrange
    trade_monitor.add_trade(sample_recommendation)

    # Mock the fetcher to return a dataframe with a price breaking resistance
    mock_fetcher.get_cached_price.return_value = {'price': 61000}

    # Mock the orchestrator to return some dummy analysis
    mock_orchestrator.run.return_value = {'supports': [], 'resistances': [], 'patterns': []}

    # Act
    await trade_monitor.check_all_trades()

    # Assert
    mock_notifier.send.assert_called_once()
    message_sent = mock_notifier.send.call_args[0][0]
    assert "Resistance Break Alert" in message_sent
    assert "60,000.00" in message_sent

@pytest.mark.anyio
async def test_pattern_status_change_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    # Arrange
    trade_monitor.add_trade(sample_recommendation)
    key = "123_BTC/USDT_1h"

    # Mock the fetcher to return some data
    mock_fetcher.get_cached_price.return_value = {'price': 60500}

    # Mock the orchestrator to return an updated pattern status
    new_analysis = {
        'supports': [], 'resistances': [],
        'patterns': [Pattern(
            name='Bull Flag',
            status='Active', # Status has changed
            timeframe='1h',
            activation_level=60000,
            invalidation_level=58000,
            target1=62000
        )]
    }
    mock_orchestrator.run.return_value = new_analysis

    # Act
    await trade_monitor.check_all_trades()

    # Assert
    assert mock_notifier.send.call_count >= 1 # Can be 1 or 2 depending on order

    # Check that both expected alerts were sent
    call_args_list = mock_notifier.send.call_args_list
    messages = [call[0][0] for call in call_args_list]
    assert any("Resistance Break Alert" in msg for msg in messages)
    # Check for the more specific "activation" message
    assert any("Trade Activated" in msg for msg in messages)

    # The trade should be removed after a terminal status update
    assert key not in trade_monitor.followed_trades
