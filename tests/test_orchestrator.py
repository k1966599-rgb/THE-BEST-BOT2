import pytest
import pandas as pd
from typing import List, Dict, Any
from src.analysis.orchestrator import AnalysisOrchestrator
from src.analysis.base_analysis import BaseAnalysis
from src.analysis.data_models import Level

# 1. Create Mock Analysis Modules
class MockSupportModule(BaseAnalysis):
    """A mock analysis module that returns a predefined list of support levels."""
    def __init__(self, mock_supports: List[Level]):
        self.mock_supports = mock_supports

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, List[Level]]:
        return {"supports": self.mock_supports, "resistances": []}

class MockResistanceModule(BaseAnalysis):
    """A mock analysis module that returns a predefined list of resistance levels."""
    def __init__(self, mock_resistances: List[Level]):
        self.mock_resistances = mock_resistances

    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, List[Level]]:
        return {"supports": [], "resistances": self.mock_resistances}


# 2. Test the Orchestrator
def test_orchestrator_returns_unmerged_levels():
    """
    Tests that the AnalysisOrchestrator, with the merging logic bypassed,
    returns the original, unmodified lists of levels.
    """
    # Arrange: Create mock levels that would normally be merged
    mock_supports = [
        Level(name="Fibonacci Support 0.618", value=100.0, level_type="support"),
        Level(name="Previous Low", value=100.1, level_type="support"), # This is within 0.5% tolerance
    ]

    mock_resistances = [
        Level(name="Fibonacci Resistance 1.618", value=200.0, level_type="resistance"),
        Level(name="Previous High", value=200.2, level_type="resistance"), # This is within 0.5% tolerance
    ]

    # Instantiate mock modules and the orchestrator
    support_module = MockSupportModule(mock_supports)
    resistance_module = MockResistanceModule(mock_resistances)
    orchestrator = AnalysisOrchestrator(analysis_modules=[support_module, resistance_module])

    # Act: Run the orchestrator
    # We can use an empty DataFrame because our mock modules don't use it.
    results = orchestrator.run(pd.DataFrame())

    # Assert: Check that the levels were NOT merged

    # Check supports
    assert len(results['supports']) == 2
    support_names = {level.name for level in results['supports']}
    assert "Confluent Zone" not in support_names
    assert "Fibonacci Support 0.618" in support_names
    assert "Previous Low" in support_names

    # Check resistances
    assert len(results['resistances']) == 2
    resistance_names = {level.name for level in results['resistances']}
    assert "Confluent Zone" not in resistance_names
    assert "Fibonacci Resistance 1.618" in resistance_names
    assert "Previous High" in resistance_names
