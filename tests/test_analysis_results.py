import sys
import os
import pytest
import pandas as pd
import json

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_config
from src.analysis.orchestrator import AnalysisOrchestrator
from src.analysis.new_support_resistance import find_new_support_resistance
from src.analysis import (
    TechnicalIndicators, TrendAnalysis, PriceChannels,
    SupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
)
from src.utils.data_preprocessor import standardize_dataframe_columns

@pytest.fixture(scope="module")
def sample_data():
    """Loads sample historical data from the BTC JSON file."""
    with open("BTC-USDT_historical.json", 'r') as f:
        data = json.load(f)['data']
    df = pd.DataFrame(data)
    df = standardize_dataframe_columns(df)
    df.set_index('timestamp', inplace=True)
    return df

@pytest.fixture(scope="module")
def orchestrator():
    """Provides a fully configured AnalysisOrchestrator instance."""
    config = get_config()
    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        PriceChannels(config=config.get('analysis')),
        SupportResistanceAnalysis(config=config.get('analysis')),
        FibonacciAnalysis(config=config.get('analysis')),
        ClassicPatterns(config=config.get('analysis')),
        TrendLineAnalysis(config=config.get('analysis'))
    ]
    return AnalysisOrchestrator(analysis_modules)


def test_new_support_resistance_data_structure(sample_data):
    """
    Tests the output data structure of the modified find_new_support_resistance function.
    """
    # Arrange
    df = sample_data

    # Act
    results = find_new_support_resistance(df)

    # Assert
    assert isinstance(results, dict)
    assert "supports" in results
    assert "resistances" in results

    # Check supports
    assert isinstance(results['supports'], list)
    if results['supports']:
        support_item = results['supports'][0]
        assert isinstance(support_item, dict)
        assert "level" in support_item
        assert "description" in support_item
        assert isinstance(support_item['level'], (float, int))
        assert isinstance(support_item['description'], str)
        assert support_item['description'] != ""

    # Check resistances
    assert isinstance(results['resistances'], list)
    if results['resistances']:
        resistance_item = results['resistances'][0]
        assert isinstance(resistance_item, dict)
        assert "level" in resistance_item
        assert "description" in resistance_item
        assert isinstance(resistance_item['level'], (float, int))
        assert isinstance(resistance_item['description'], str)
        assert resistance_item['description'] != ""

def test_orchestrator_produces_all_keys(orchestrator, sample_data):
    """
    Tests that the AnalysisOrchestrator runs and produces a result dictionary
    containing all expected keys from its modules.
    """
    # Act
    results = orchestrator.run(sample_data)

    # Assert
    assert isinstance(results, dict)
    expected_keys = [
        'TechnicalIndicators',
        'TrendAnalysis',
        'PriceChannels',
        'SupportResistanceAnalysis',
        'FibonacciAnalysis',
        'ClassicPatterns',
        'TrendLineAnalysis',
        'NewSupportResistance' # This is added separately by the orchestrator
    ]
    for key in expected_keys:
        assert key in results, f"Orchestrator result missing expected key: {key}"

    # Also check the format of the NewSupportResistance part specifically
    new_sr_results = results['NewSupportResistance']
    assert "supports" in new_sr_results
    assert isinstance(new_sr_results['supports'], list)
    if new_sr_results['supports']:
        assert "description" in new_sr_results['supports'][0]
