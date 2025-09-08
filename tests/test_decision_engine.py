import pytest
import sys
import os

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.decision_engine.engine import DecisionEngine
from src.config import get_config

@pytest.fixture
def decision_engine():
    """Pytest fixture to create a DecisionEngine instance with default config."""
    config = get_config()
    return DecisionEngine(config)

@pytest.fixture
def sample_bullish_analysis():
    """Sample analysis results that should lead to a 'Buy' recommendation."""
    return {
        'TechnicalIndicators': {'total_score': 5, 'rsi_divergence': None, 'macd_divergence': None},
        'TrendAnalysis': {'total_score': 3},
        'PriceChannels': {'total_score': 1},
        'SupportResistanceAnalysis': {'sr_score': 2},
        'FibonacciAnalysis': {'fib_score': 1},
        'ClassicPatterns': {'pattern_score': 0, 'found_patterns': []}
    }

@pytest.fixture
def sample_bearish_analysis():
    """Sample analysis results that should lead to a 'Sell' recommendation."""
    return {
        'TechnicalIndicators': {'total_score': -4, 'rsi_divergence': None, 'macd_divergence': None},
        'TrendAnalysis': {'total_score': -3},
        'PriceChannels': {'total_score': -1},
        'SupportResistanceAnalysis': {'sr_score': -2},
        'FibonacciAnalysis': {'fib_score': -1},
        'ClassicPatterns': {'pattern_score': 0, 'found_patterns': []}
    }

@pytest.fixture
def sample_conflict_analysis():
    """
    Sample results with a bearish score but a bullish pattern forming.
    The score is made sufficiently negative to trigger a 'Sell' action initially.
    """
    return {
        'TechnicalIndicators': {'total_score': -8}, # Changed from -4 to make score more negative
        'TrendAnalysis': {'total_score': -3},
        'ClassicPatterns': {
            'pattern_score': 2,
            'found_patterns': [{
                'name': 'وتد صاعد (Falling Wedge)',
                'status': 'قيد التكوين 🟡',
                'confidence': 80
            }]
        }
    }

def test_make_bullish_recommendation(decision_engine, sample_bullish_analysis):
    """Test that bullish analysis results in a 'Buy' or 'Strong Buy' action."""
    recommendation = decision_engine.make_recommendation(sample_bullish_analysis, "BTC/USDT", "1h")
    assert 'شراء' in recommendation['main_action']
    assert recommendation['total_score'] > 0
    assert recommendation['conflict_note'] is None

def test_make_bearish_recommendation(decision_engine, sample_bearish_analysis):
    """Test that bearish analysis results in a 'Sell' or 'Strong Sell' action."""
    recommendation = decision_engine.make_recommendation(sample_bearish_analysis, "BTC/USDT", "1h")
    assert 'بيع' in recommendation['main_action']
    assert recommendation['total_score'] < 0
    assert recommendation['conflict_note'] is None

def test_conflict_resolution(decision_engine, sample_conflict_analysis):
    """Test that a forming bullish pattern overrides a bearish score."""
    recommendation = decision_engine.make_recommendation(sample_conflict_analysis, "BTC/USDT", "1h")
    # The bearish score should be overridden by the forming bullish pattern
    assert 'انتظار' in recommendation['main_action']
    assert recommendation['conflict_note'] is not None
    assert 'إيجابي' in recommendation['conflict_note']

def test_rank_recommendations(decision_engine):
    """Test the ranking logic."""
    recs = [
        # Strong buy, should be ranked first
        {'main_action': 'شراء قوي', 'total_score': 25, 'confidence': 90, 'raw_analysis': {'TechnicalIndicators': {}}},
        # Wait signal, should be ranked last
        {'main_action': 'انتظار ⏳', 'total_score': 5, 'confidence': 70, 'raw_analysis': {'TechnicalIndicators': {}}},
        # Regular sell, should be in the middle
        {'main_action': 'بيع', 'total_score': -12, 'confidence': 85, 'raw_analysis': {'TechnicalIndicators': {}}},
        # Buy with divergence, should get a bonus and rank high
        {'main_action': 'شراء', 'total_score': 15, 'confidence': 80, 'raw_analysis': {'TechnicalIndicators': {'rsi_divergence': 'Bullish'}}}
    ]

    ranked = decision_engine.rank_recommendations(recs)

    # Check that the list is sorted by rank_score
    assert all(ranked[i]['rank_score'] >= ranked[i+1]['rank_score'] for i in range(len(ranked)-1))

    # Check the expected order of actions
    assert 'شراء قوي' in ranked[0]['main_action']
    assert 'شراء' in ranked[1]['main_action'] # The one with divergence
    assert 'بيع' in ranked[2]['main_action']
    assert 'انتظار' in ranked[3]['main_action']

    # Verify the divergence bonus was applied
    assert ranked[1]['rank_score'] > (15 * 0.80 * 1.0) # Should be greater than without the 1.2x bonus
    # Verify the wait penalty was applied
    assert ranked[3]['rank_score'] < (5 * 0.70 * 1.0) # Should be less than without the 0.1x penalty
