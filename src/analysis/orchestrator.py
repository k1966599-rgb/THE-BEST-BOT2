import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from .indicators import apply_all_indicators
from .data_models import Level, Pattern

class AnalysisOrchestrator:
    """Coordinates and runs all analysis modules.

    This class takes a list of analysis modules, runs them sequentially,
    and aggregates their results. It handles applying indicators, providing
    context between modules (like trend context for pattern detection), and
    merging confluent support and resistance levels.
    """
    def __init__(self, analysis_modules: List[BaseAnalysis]):
        """Initializes the AnalysisOrchestrator.

        Args:
            analysis_modules (List[BaseAnalysis]): A list of instantiated
                analysis module objects to be run.
        """
        self.analysis_modules = analysis_modules

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Runs all analysis modules and aggregates their results.

        The process involves:
        1. Applying a standard set of technical indicators to the data.
        2. Running trend analysis first to establish market context.
        3. Running all other analysis modules.
        4. Aggregating results into master lists of supports, resistances,
           and patterns.
        5. Merging confluent support and resistance levels.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.

        Returns:
            Dict[str, Any]: A dictionary containing the aggregated and
            processed analysis results, including 'supports', 'resistances',
            'patterns', and 'other_analysis'.
        """
        df_with_indicators = apply_all_indicators(df.copy())

        master_supports: List[Level] = []
        master_resistances: List[Level] = []
        master_patterns: List[Pattern] = []
        other_results: Dict[str, Any] = {}

        trend_results = {}

        # Run TrendAnalysis first to get the context
        for module in self.analysis_modules:
            if module.__class__.__name__ == 'TrendAnalysis':
                trend_results = module.analyze(df_with_indicators)
                other_results['TrendAnalysis'] = trend_results
                break

        for module in self.analysis_modules:
            module_name = module.__class__.__name__

            # Skip TrendAnalysis as it has already been run
            if module_name == 'TrendAnalysis':
                continue

            # Pass trend context to ClassicPatterns
            if module_name == 'ClassicPatterns':
                result = module.analyze(df_with_indicators, trend_context=trend_results)
            else:
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

        # Merge confluent levels
        merged_supports = self._merge_confluent_levels(master_supports)
        merged_resistances = self._merge_confluent_levels(master_resistances)

        return {
            'supports': merged_supports,
            'resistances': merged_resistances,
            'patterns': master_patterns,
            'other_analysis': other_results
        }

    def _merge_confluent_levels(self, levels: List[Level], tolerance: float = 0.005) -> List[Level]:
        """Merges a list of S/R levels that are very close to each other.

        This method iterates through a sorted list of levels and groups them
        into clusters based on a percentage tolerance. Levels within the same
        cluster are merged into a single, stronger level.

        Args:
            levels (List[Level]): A list of support or resistance Level objects.
            tolerance (float, optional): The percentage difference allowed for
                levels to be considered part of the same cluster. Defaults to
                0.005 (0.5%).

        Returns:
            List[Level]: A new list of levels with confluent levels merged.
        """
        if not levels:
            return []

        # Sort by value to make clustering easier
        levels.sort(key=lambda x: x.value)

        merged = []
        cluster = [levels[0]]

        for level in levels[1:]:
            cluster_avg = np.mean([l.value for l in cluster])
            if (level.value - cluster_avg) / cluster_avg <= tolerance:
                cluster.append(level)
            else:
                if len(cluster) > 1:
                    # Create a new confluent level
                    new_value = np.mean([l.value for l in cluster])
                    new_name = "منطقة تقاطع دعم" if cluster[0].level_type == 'support' else "منطقة تقاطع مقاومة"
                    # You can get more creative with naming by combining names
                    merged.append(Level(name=new_name, value=new_value, level_type=cluster[0].level_type, quality="قوي جدا"))
                else:
                    merged.append(cluster[0])
                cluster = [level]

        # Handle the last cluster
        if len(cluster) > 1:
            new_value = np.mean([l.value for l in cluster])
            new_name = "منطقة تقاطع دعم" if cluster[0].level_type == 'support' else "منطقة تقاطع مقاومة"
            merged.append(Level(name=new_name, value=new_value, level_type=cluster[0].level_type, quality="قوي جدا"))
        else:
            merged.append(cluster[0])

        return merged
