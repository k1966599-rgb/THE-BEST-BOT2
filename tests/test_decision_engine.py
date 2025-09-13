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
        name='Bullish Double Bottom',
        status='Active',
        timeframe='1h',
        activation_level=100,
        invalidation_level=90,
        target1=110,
        target2=115,
        confidence=80.0
    )

@pytest.fixture
def sample_pending_pattern():
    return Pattern(
        name='Bull Flag',
        status='Forming',
        timeframe='4h',
        activation_level=105,
        invalidation_level=95,
        target1=115,
        target2=120
    )

def test_make_bullish_recommendation(decision_engine, sample_bullish_pattern):
    """Test that a bullish pattern results in a 'Buy' action."""
    analysis_results = {'patterns': [sample_bullish_pattern], 'supports': [], 'resistances': [], 'other_analysis': {}}
    df = pd.DataFrame({'close': [101]*21, 'volume': [100]*21, 'sma_20': [99]*21, 'sma_50': [98]*21})
    df.index = pd.to_datetime(pd.to_datetime(range(len(df)), unit='D'))


    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "1h", chat_id=123)

    assert 'Buy' in recommendation['main_action']
    assert recommendation['trade_setup'] is not None
    assert recommendation['trade_setup'].target1 == 110
    assert len(recommendation['trade_setup'].confirmation_conditions) > 0
    assert "إغلاق 3 شموع 1h متتالية above مستوى $100.00" in recommendation['trade_setup'].confirmation_conditions[0]

def test_make_pending_recommendation(decision_engine, sample_pending_pattern):
    """Test that a pending pattern results in a 'Wait' action."""
    analysis_results = {'patterns': [sample_pending_pattern], 'supports': [], 'resistances': []}
    df = pd.DataFrame({'close': [102]})

    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "4h")

    assert 'Wait' in recommendation['main_action']
    assert recommendation['trade_setup'] is None

def test_rank_recommendations(decision_engine):
    """Test the simplified ranking logic."""
    recs = [
        {'main_action': 'Buy', 'total_score': 75, 'confidence': 75},
        {'main_action': 'Sell', 'total_score': -50, 'confidence': 50},
        {'main_action': 'Wait ⏳', 'total_score': 0, 'confidence': 50},
    ]

    ranked = decision_engine.rank_recommendations(recs)

    assert ranked[0]['total_score'] == 75
    assert ranked[1]['total_score'] == -50
    assert ranked[2]['total_score'] == 0

def test_low_confidence_pattern_is_wait(decision_engine):
    """Test that a pattern with low confidence results in a 'Wait' action."""
    low_conf_pattern = Pattern(
        name='Bull Flag', status='Active', timeframe='1h',
        activation_level=100, invalidation_level=90, target1=110, confidence=40.0
    )
    analysis_results = {'patterns': [low_conf_pattern], 'supports': [], 'resistances': []}
    df = pd.DataFrame({'close': [101]})

    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "1h", chat_id=123)

    assert 'Wait' in recommendation['main_action']

def test_conflict_resolution_with_trend(decision_engine, sample_bullish_pattern):
    """Test that a bullish pattern in a downtrend results in a 'Wait' action."""
    analysis_results = {
        'patterns': [sample_bullish_pattern],
        'supports': [],
        'resistances': [],
        'other_analysis': {
            'TrendAnalysis': {'trend_direction': 'Downtrend'}
        }
    }
    df = pd.DataFrame({'close': [101]})

    recommendation = decision_engine.make_recommendation(analysis_results, df, "BTC/USDT", "1h", chat_id=123)

    assert 'Wait' in recommendation['main_action']
    assert recommendation['conflict_note'] is not None

def test_generate_intelligent_confirmations(decision_engine, sample_bullish_pattern):
    """Test the generation of new, intelligent confirmation conditions."""
    data = {
        'close': [98] * 20 + [101],
        'volume': [100] * 20 + [200],
        'sma_20': [97] * 20 + [99],
        'sma_50': [96] * 20 + [98]
    }
    mock_df = pd.DataFrame(data)
    mock_df.index = pd.to_datetime(pd.to_datetime(range(len(mock_df)), unit='D'))

    mock_analysis_results = {
        'patterns': [sample_bullish_pattern],
        'supports': [],
        'resistances': [],
        'other_analysis': {
            'TrendAnalysis': {'trend_direction': 'Uptrend', 'confidence': 80}
        }
    }

    recommendation = decision_engine.make_recommendation(mock_analysis_results, mock_df, "BTC/USDT", "1h", chat_id=123)

    assert recommendation['trade_setup'] is not None
    conditions = recommendation['trade_setup'].confirmation_conditions

    assert len(conditions) == 1
