import sys
import os
import pytest
from unittest.mock import MagicMock

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.monitoring.trade_monitor import TradeMonitor
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
    monitor = TradeMonitor(config, mock_fetcher, mock_orchestrator, mock_notifier)
    monitor.proximity_threshold = 0.01 # 1%
    return monitor

@pytest.fixture
def sample_recommendation():
    """A sample recommendation object to add to the monitor."""
    pattern = Pattern(name='Bull Flag', status='Forming', timeframe='1h', activation_level=60000, invalidation_level=58000, target1=62000, target2=64000)
    return {
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'trade_setup': TradeSetup(
            chat_id=123, symbol='BTC/USDT', timeframe='1h',
            pattern_name='Bull Flag', pattern_status='Forming',
            entry_price=60000, stop_loss=58000, target1=62000, target2=64000,
            raw_pattern_data=pattern.__dict__
        ),
        'raw_analysis': {
            'supports': [Level(name='Minor Support', value=59000, level_type='support')],
            'resistances': [Level(name='Major Resistance', value=61000, level_type='resistance')],
            'patterns': [pattern]
        }
    }

def test_add_trade(trade_monitor, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    key = "123_BTC/USDT_1h"
    assert key in trade_monitor.followed_trades
    assert trade_monitor.followed_trades[key]['symbol'] == 'BTC/USDT'

@pytest.mark.anyio
async def test_support_hit_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    mock_fetcher.get_cached_price.return_value = {'price': 59050} # Price near support
    mock_orchestrator.run.return_value = {} # Dummy analysis

    await trade_monitor.check_all_trades()

    mock_notifier.send.assert_called_once()
    message = mock_notifier.send.call_args[0][0]
    assert "تنبيه متابعة" in message
    assert "ارتداد السعر من دعم" in message
    assert "59,000" in message
    assert "نصيحة: قد يكون ارتدادًا صعوديًا" in message

@pytest.mark.anyio
async def test_resistance_hit_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    mock_fetcher.get_cached_price.return_value = {'price': 60950} # Price near resistance
    mock_orchestrator.run.return_value = {}

    await trade_monitor.check_all_trades()

    mock_notifier.send.assert_called_once()
    message = mock_notifier.send.call_args[0][0]
    assert "تنبيه متابعة" in message
    assert "ملامسة السعر لمقاومة" in message
    assert "61,000" in message
    assert "نصيحة: قد يواجه السعر صعوبة في الاختراق" in message

@pytest.mark.anyio
async def test_stop_loss_hit_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    key = "123_BTC/USDT_1h"
    mock_fetcher.get_cached_price.return_value = {'price': 57900} # Price below SL
    mock_orchestrator.run.return_value = {}

    await trade_monitor.check_all_trades()

    mock_notifier.send.assert_called_once()
    message = mock_notifier.send.call_args[0][0]
    assert "وقف الخسارة" in message
    assert "58,000" in message
    assert key not in trade_monitor.followed_trades # Trade should be removed

@pytest.mark.anyio
async def test_target_hit_alert(trade_monitor, mock_fetcher, mock_orchestrator, mock_notifier, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    mock_fetcher.get_cached_price.return_value = {'price': 62100} # Price above target 1
    mock_orchestrator.run.return_value = {}

    await trade_monitor.check_all_trades()

    mock_notifier.send.assert_called_once()
    message = mock_notifier.send.call_args[0][0]
    assert "تحقيق هدف" in message
    assert "62,000" in message
    # Trade should still be monitored for target 2
    assert "123_BTC/USDT_1h" in trade_monitor.followed_trades
