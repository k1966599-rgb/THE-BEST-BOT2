import sys
import os
import pytest
import pandas as pd
import json

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_config
from src.analysis.orchestrator import AnalysisOrchestrator
from src.analysis.data_models import Level, Pattern
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
    # Note: We are not including NewSupportResistance here as it's not a class-based module
    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        PriceChannels(config=config.get('analysis')),
        SupportResistanceAnalysis(config=config.get('analysis')),
        FibonacciAnalysis(config=config.get('analysis')),
        ClassicPatterns(config=config.get('analysis')),
        TrendLineAnalysis(config=config.get('analysis'))
    ]
    # Pass config to orchestrator
    return AnalysisOrchestrator(analysis_modules, config=config)

def test_orchestrator_output_structure(orchestrator, sample_data):
    """
    Tests that the refactored AnalysisOrchestrator produces the new, standardized data structure.
    """
    # Act
    results = orchestrator.run(sample_data)

    # Assert
    assert isinstance(results, dict)
    expected_keys = ['supports', 'resistances', 'patterns', 'other_analysis']
    for key in expected_keys:
        assert key in results, f"Orchestrator result missing expected key: {key}"

    # Check supports list
    assert isinstance(results['supports'], list)
    if results['supports']:
        assert all(isinstance(item, Level) for item in results['supports'])
        assert all(item.level_type == 'support' for item in results['supports'])

    # Check resistances list
    assert isinstance(results['resistances'], list)
    if results['resistances']:
        assert all(isinstance(item, Level) for item in results['resistances'])
        assert all(item.level_type == 'resistance' for item in results['resistances'])

    # Check patterns list
    assert isinstance(results['patterns'], list)
    if results['patterns']:
        assert all(isinstance(item, Pattern) for item in results['patterns'])

    # Check that other analysis results are still present
    assert 'TrendAnalysis' in results['other_analysis']

def test_orchestrator_level_confluence(orchestrator):
    """
    Tests that the orchestrator, with default config, does NOT merge confluent levels.
    """
    # Arrange
    # Mock the analyze methods of modules to return specific, overlapping levels
    mock_support_level_1 = Level(name="Fibonacci Support", value=100.5, level_type='support', quality='Strong')
    mock_support_level_2 = Level(name="Horizontal Support", value=100.2, level_type='support', quality='Secondary')
    mock_support_level_3 = Level(name="Channel Support", value=95.0, level_type='support', quality='Bottom') # This one is not close

    # This mocks the return value of the analyze() method for each class instance
    orchestrator.analysis_modules[2].analyze = lambda df, **kwargs: {'supports': [mock_support_level_3], 'resistances': []} # PriceChannels
    orchestrator.analysis_modules[4].analyze = lambda df, **kwargs: {'supports': [mock_support_level_1, mock_support_level_2], 'resistances': []} # FibonacciAnalysis

    # Create a dummy DataFrame
    df = pd.DataFrame({'close': [105]})

    # Act
    results = orchestrator.run(df)

    # Assert
    supports = results['supports']
    # With merging now disabled by default, all 3 levels should be present.
    assert len(supports) == 3

    # Check that no merged level was created
    assert not any("Confluent" in s.name for s in supports)
