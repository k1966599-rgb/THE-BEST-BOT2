import pytest
import pandas as pd
from src.analysis.patterns.base_pattern import BasePattern
from src.config import get_config

# A concrete implementation of BasePattern for testing purposes
class ConcretePattern(BasePattern):
    def check(self):
        pass

@pytest.fixture
def base_pattern_instance():
    """Provides a BasePattern instance with sample data for testing."""
    config = get_config()['analysis']
    # Standard column names are lowercase 'r'
    data = {
        'atrr_14': [1.0, 1.1, 1.2, 1.3, 1.4]
    }
    df = pd.DataFrame(data)
    # The other parameters are not needed for testing the stop-loss method
    return ConcretePattern(df=df, config=config, highs=[], lows=[], current_price=100, price_tolerance=0.03)

def test_calculate_atr_stop_loss_long(base_pattern_instance):
    """Tests the ATR-based stop-loss calculation for a long position."""
    price_level = 100.0
    atr_multiplier = 2.0
    # Last ATR value is 1.4
    expected_stop_loss = price_level - (1.4 * atr_multiplier)

    stop_loss = base_pattern_instance._calculate_atr_stop_loss(price_level, atr_multiplier, is_long=True)

    assert stop_loss == pytest.approx(expected_stop_loss)

def test_calculate_atr_stop_loss_short(base_pattern_instance):
    """Tests the ATR-based stop-loss calculation for a short position."""
    price_level = 100.0
    atr_multiplier = 1.5
    # Last ATR value is 1.4
    expected_stop_loss = price_level + (1.4 * atr_multiplier)

    stop_loss = base_pattern_instance._calculate_atr_stop_loss(price_level, atr_multiplier, is_long=False)

    assert stop_loss == pytest.approx(expected_stop_loss)

def test_calculate_atr_stop_loss_fallback(base_pattern_instance):
    """Tests the fallback to percentage-based stop-loss if ATR is not available."""
    # Create a dataframe without the ATR column
    base_pattern_instance.df = pd.DataFrame({'close': [100]})
    price_level = 100.0

    # Test long fallback
    expected_long_stop = 99.0
    long_stop = base_pattern_instance._calculate_atr_stop_loss(price_level, is_long=True)
    assert long_stop == pytest.approx(expected_long_stop)

    # Test short fallback
    expected_short_stop = 101.0
    short_stop = base_pattern_instance._calculate_atr_stop_loss(price_level, is_long=False)
    assert short_stop == pytest.approx(expected_short_stop)
