import pandas as pd
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from .indicators import apply_all_indicators

class AnalysisOrchestrator:
    def __init__(self, analysis_modules: List[BaseAnalysis]):
        self.analysis_modules = analysis_modules

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        df_with_indicators = apply_all_indicators(df.copy())
        analysis_results = {}
        for module in self.analysis_modules:
            module_name = module.__class__.__name__
            analysis_results[module_name] = module.analyze(df_with_indicators)
        return analysis_results
