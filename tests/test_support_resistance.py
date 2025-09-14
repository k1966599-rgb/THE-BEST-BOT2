import pytest
import pandas as pd
from src.analysis.support_resistance import SupportResistanceAnalysis
from src.analysis.patterns.pattern_utils import cluster_levels
from src.config import get_config
from unittest.mock import patch

@pytest.fixture
def sr_analysis_instance():
    """Provides a SupportResistanceAnalysis instance with a test-friendly config."""
    config = get_config()
    # Override the lookback for the '1h' timeframe specifically for this test
    config['analysis']['TIMEFRAME_OVERRIDES']['1h']['SR_LOOKBACK'] = 50
    return SupportResistanceAnalysis(config=config['analysis'], timeframe='1h')

def test_cluster_levels_logic():
    """
    Tests the cluster_levels function to ensure it's robust and consistent.
    """
    levels1 = [100, 100.1, 100.2, 105, 105.1]
    levels2 = [105.1, 100, 105, 100.1, 100.2]

    clusters1 = cluster_levels(levels1, tolerance=0.5)
    clusters2 = cluster_levels(levels2, tolerance=0.5)

    assert clusters1 == clusters2
    expected_clusters = [100.1, 105.05]
    assert len(clusters1) == len(expected_clusters)
    for i in range(len(clusters1)):
        assert clusters1[i] == pytest.approx(expected_clusters[i])

@patch('src.analysis.support_resistance.get_pivots')
def test_analyze_logic(mock_get_pivots, sr_analysis_instance):
    """
    Tests the analyze method with mock pivots to ensure it processes them correctly.
    """
    mock_get_pivots.return_value = (
        [{'price': 110}, {'price': 112}],
        [{'price': 90}, {'price': 92}]
    )
    # Create a DataFrame larger than the lookback period
    df = pd.DataFrame({
        'high': [115] * 100,
        'low': [85] * 100,
        'close': [100] * 100
    })

    result = sr_analysis_instance.analyze(df)

    support_names = [s.name for s in result['supports']]
    resistance_names = [r.name for r in result['resistances']]

    assert "دعم ثانوي" in support_names
    assert "مقاومة ثانوية" in resistance_names
    assert "دعم عام سابق" in support_names
    assert "مقاومة عامة سابقة" in resistance_names
