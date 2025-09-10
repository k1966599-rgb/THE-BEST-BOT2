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

@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send = MagicMock()
    return notifier

@pytest.fixture
def mock_fetcher():
    return MagicMock()

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
    return {
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'trade_setup': MagicMock(
            chat_id=123,
            symbol='BTC/USDT',
            timeframe='1h'
        ),
        'raw_analysis': {
            'NewSupportResistance': {
                'supports': [{'level': 50000, 'description': 'دعم قوي'}],
                'resistances': [{'level': 60000, 'description': 'مقاومة حرجة'}]
            },
            'ClassicPatterns': {
                'found_patterns': [{
                    'name': 'مثلث صاعد',
                    'status': 'قيد التكوين'
                }]
            }
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
    mock_fetcher.fetch_historical_data.return_value = {
        'data': [{
            'timestamp': 1, 'open': 60000, 'high': 61500, 'low': 59000, 'close': 61000, 'volume': 100
        }]
    }
    mock_fetcher.get_cached_price.return_value = {'price': 61000}

    # Mock the orchestrator to return some dummy analysis
    mock_orchestrator.run.return_value = {}

    # Act
    await trade_monitor.check_all_trades()

    # Assert
    mock_notifier.send.assert_called_once()
    message_sent = mock_notifier.send.call_args[0][0]
    assert "تنبيه اختراق مقاومة" in message_sent
    assert "60,000.00" in message_sent

@pytest.mark.anyio
async def test_pattern_status_change_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    # Arrange
    trade_monitor.add_trade(sample_recommendation)
    key = "123_BTC/USDT_1h"

    # Mock the fetcher to return some data
    mock_fetcher.get_cached_price.return_value = {'price': 55000}
    mock_fetcher.fetch_historical_data.return_value = {
        'data': [{
            'timestamp': 1, 'open': 54000, 'high': 55500, 'low': 53000, 'close': 55000, 'volume': 100
        }]
    }

    # Mock the orchestrator to return an updated pattern status
    new_analysis = {
        'ClassicPatterns': {
            'found_patterns': [{
                'name': 'مثلث صاعد',
                'status': 'مفعل' # Status has changed
            }]
        }
    }
    mock_orchestrator.run.return_value = new_analysis

    # Act
    await trade_monitor.check_all_trades()

    # Assert
    mock_notifier.send.assert_called_once()
    message_sent = mock_notifier.send.call_args[0][0]
    assert "تنبيه تحديث نموذج" in message_sent
    assert "مفعل" in message_sent

    # The trade should be removed after a terminal status update
    assert key not in trade_monitor.followed_trades
