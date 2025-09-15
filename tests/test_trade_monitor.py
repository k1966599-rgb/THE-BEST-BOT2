import pytest
from unittest.mock import MagicMock, AsyncMock
import pandas as pd
import anyio

from src.config import get_config
from src.analysis.data_models import Level
from src.decision_engine.trade_setup import TradeSetup
from src.monitoring.trade_monitor import TradeMonitor

@pytest.fixture
def mock_fetcher():
    fetcher = MagicMock()
    fetcher.fetch_historical_data = AsyncMock(return_value={
        'data': [{'close': 100, 'high': 110, 'low': 90, 'timestamp': 12345}]
    })
    fetcher.get_cached_price.return_value = {'price': 100}
    return fetcher

@pytest.fixture
def mock_notifier():
    return MagicMock()

@pytest.fixture
def trade_monitor(mock_fetcher, mock_notifier):
    config = get_config()
    monitor = TradeMonitor(config, mock_fetcher, mock_notifier)
    return monitor

@pytest.fixture
def sample_recommendation():
    trade_setup = TradeSetup(
        symbol='BTC-USDT',
        timeframe='1h',
        entry_price=105.0,
        stop_loss=95.0,
        target1=115.0,
        target2=125.0,
        chat_id=123,
        pattern_name='Test Pattern',
        pattern_status='Test Status'
    )
    return {
        'trade_setup': trade_setup,
        'raw_analysis': {
            'supports': [Level(name='Test Support', value=100.0, level_type='support')],
            'resistances': [Level(name='Test Resistance', value=110.0, level_type='resistance')]
        }
    }

def test_add_trade(trade_monitor, sample_recommendation):
    trade_monitor.add_trade(sample_recommendation)
    key = "123_BTC-USDT_1h"
    assert key in trade_monitor.followed_trades
    assert trade_monitor.followed_trades[key]['symbol'] == 'BTC-USDT'

@pytest.mark.anyio
async def test_support_hit_alert(trade_monitor, mock_fetcher, mock_notifier, sample_recommendation):
    mock_fetcher.get_cached_price.return_value = {'price': 100.1}
    trade_monitor.add_trade(sample_recommendation)
    await trade_monitor.check_all_trades()
    mock_notifier.send.assert_called_once()
    assert "ارتداد السعر من دعم" in mock_notifier.send.call_args[0][0]

@pytest.mark.anyio
async def test_resistance_hit_alert(trade_monitor, mock_fetcher, mock_notifier, sample_recommendation):
    mock_fetcher.get_cached_price.return_value = {'price': 109.9}
    trade_monitor.add_trade(sample_recommendation)
    await trade_monitor.check_all_trades()
    mock_notifier.send.assert_called_once()
    assert "ملامسة السعر لمقاومة" in mock_notifier.send.call_args[0][0]

@pytest.mark.anyio
async def test_stop_loss_hit_alert(trade_monitor, mock_fetcher, mock_notifier, sample_recommendation):
    mock_fetcher.get_cached_price.return_value = {'price': 94.0}
    trade_monitor.add_trade(sample_recommendation)
    await trade_monitor.check_all_trades()
    mock_notifier.send.assert_called_once()
    assert "وقف الخسارة" in mock_notifier.send.call_args[0][0]
    assert not trade_monitor.followed_trades # Trade should be removed

@pytest.mark.anyio
async def test_target_hit_alert(trade_monitor, mock_fetcher, mock_notifier, sample_recommendation):
    mock_fetcher.get_cached_price.return_value = {'price': 115.1}
    trade_monitor.add_trade(sample_recommendation)
    await trade_monitor.check_all_trades()
    mock_notifier.send.assert_called_once()
    assert "تحقيق هدف" in mock_notifier.send.call_args[0][0]
