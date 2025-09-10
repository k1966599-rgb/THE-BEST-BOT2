import pytest
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.decision_engine.engine import DecisionEngine
from src.config import get_config
from src.analysis.data_models import Pattern

@pytest.fixture
def decision_engine():
    config = get_config()
    return DecisionEngine(config)

@pytest.fixture
def sample_bullish_pattern():
    return Pattern(
        name='قاع مزدوج',
        status='مفعل',
        timeframe='1h',
        activation_level=100,
        invalidation_level=90,
        target1=110,
        target2=115
    )

@pytest.fixture
def sample_pending_pattern():
    return Pattern(
        name='علم صاعد',
        status='قيد التكوين',
        timeframe='4h',
        activation_level=105,
        invalidation_level=95,
        target1=115,
        target2=120
    )

def test_make_bullish_recommendation(decision_engine, sample_bullish_pattern):
    """Test that a bullish pattern results in a 'Buy' action."""
    analysis_results = {'patterns': [sample_bullish_pattern], 'supports': [], 'resistances': []}
    df = pd.DataFrame({'close': [101]})

    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "1h", chat_id=123)

    assert 'شراء' in recommendation['main_action']
    assert recommendation['trade_setup'] is not None
    assert recommendation['trade_setup'].target1 == 110

def test_make_pending_recommendation(decision_engine, sample_pending_pattern):
    """Test that a pending pattern results in a 'Wait' action."""
    analysis_results = {'patterns': [sample_pending_pattern], 'supports': [], 'resistances': []}
    df = pd.DataFrame({'close': [102]})

    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "4h")

    assert 'انتظار' in recommendation['main_action']
    # TradeSetup should not be created if the pattern is just pending and no chat_id is provided
    assert recommendation['trade_setup'] is None

def test_rank_recommendations(decision_engine):
    """Test the simplified ranking logic."""
    recs = [
        # Stronger signal, should be first
        {'main_action': 'شراء', 'total_score': 75, 'confidence': 75},
        # Weaker signal
        {'main_action': 'بيع', 'total_score': -50, 'confidence': 50},
        # Wait signal, should be last
        {'main_action': 'انتظار ⏳', 'total_score': 0, 'confidence': 50},
    ]

    ranked = decision_engine.rank_recommendations(recs)

    assert ranked[0]['total_score'] == 75
    assert ranked[1]['total_score'] == -50
    assert ranked[2]['total_score'] == 0
