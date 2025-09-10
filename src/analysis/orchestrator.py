import pandas as pd
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from .indicators import apply_all_indicators
from .data_models import Level, Pattern

class AnalysisOrchestrator:
    def __init__(self, analysis_modules: List[BaseAnalysis]):
        self.analysis_modules = analysis_modules

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs all analysis modules and aggregates their results into a standardized format.
        """
        df_with_indicators = apply_all_indicators(df.copy())

        master_supports: List[Level] = []
        master_resistances: List[Level] = []
        master_patterns: List[Pattern] = []
        other_results: Dict[str, Any] = {}

        for module in self.analysis_modules:
            module_name = module.__class__.__name__
            result = module.analyze(df_with_indicators)

            # Check the type of result and aggregate accordingly
            if isinstance(result, dict) and 'supports' in result and 'resistances' in result:
                master_supports.extend(result.get('supports', []))
                master_resistances.extend(result.get('resistances', []))
            elif isinstance(result, list) and all(isinstance(p, Pattern) for p in result):
                master_patterns.extend(result)
            else:
                # For modules that don't return S/R or Patterns (e.g., TrendAnalysis)
                other_results[module_name] = result

        # Sort the master lists
        master_supports.sort(key=lambda x: x.value, reverse=True)
        master_resistances.sort(key=lambda x: x.value)
        # Sorting patterns can be done later based on confidence or status

        return {
            'supports': master_supports,
            'resistances': master_resistances,
            'patterns': master_patterns,
            'other_analysis': other_results
        }
