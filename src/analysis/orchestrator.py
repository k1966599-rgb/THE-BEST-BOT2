import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from .indicators import apply_all_indicators
from .data_models import Level, Pattern

class AnalysisOrchestrator:
    """Coordinates and runs all analysis modules."""
    def __init__(self, analysis_modules: List[BaseAnalysis]):
        self.analysis_modules = analysis_modules

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        df_with_indicators = apply_all_indicators(df.copy())

        master_supports: List[Level] = []
        master_resistances: List[Level] = []
        master_patterns: List[Pattern] = []
        other_results: Dict[str, Any] = {}
        trend_results = {}

        for module in self.analysis_modules:
            if module.__class__.__name__ == 'TrendAnalysis':
                trend_results = module.analyze(df_with_indicators)
                other_results['TrendAnalysis'] = trend_results
                break

        for module in self.analysis_modules:
            module_name = module.__class__.__name__
            if module_name == 'TrendAnalysis':
                continue
            if module_name == 'ClassicPatterns':
                result = module.analyze(df_with_indicators, trend_context=trend_results)
            else:
                result = module.analyze(df_with_indicators)

            if isinstance(result, dict) and 'supports' in result and 'resistances' in result:
                master_supports.extend(result.get('supports', []))
                master_resistances.extend(result.get('resistances', []))
            elif isinstance(result, list) and all(isinstance(p, Pattern) for p in result):
                master_patterns.extend(result)
            else:
                other_results[module_name] = result

        master_supports.sort(key=lambda x: x.value, reverse=True)
        master_resistances.sort(key=lambda x: x.value)

        merged_supports = self._merge_confluent_levels(master_supports)
        merged_resistances = self._merge_confluent_levels(master_resistances)

        return {
            'supports': merged_supports,
            'resistances': merged_resistances,
            'patterns': master_patterns,
            'other_analysis': other_results
        }

    def _merge_confluent_levels(self, levels: List[Level], tolerance: float = 0.005) -> List[Level]:
        if not levels:
            return []

        levels.sort(key=lambda x: x.value)
        merged = []
        if not levels:
            return merged

        cluster = [levels[0]]

        for level in levels[1:]:
            cluster_avg = np.mean([l.value for l in cluster])
            if (level.value - cluster_avg) / cluster_avg <= tolerance:
                cluster.append(level)
            else:
                # Process the completed cluster
                if len(cluster) > 1:
                    new_value = np.mean([l.value for l in cluster])
                    base_names = set()
                    for l in cluster:
                        base_name = l.name.split(' ')[0]
                        if 'Fibonacci' in base_name:
                            base_names.add('Fibonacci')
                        elif 'Channel' in base_name:
                            base_names.add('Channel')
                        elif 'Trend' in base_name:
                            base_names.add('Trend')
                        else:
                            base_names.add('General')

                    name_str = ', '.join(sorted(list(base_names)))
                    new_name = f"Confluent Zone ({name_str})"
                    merged.append(Level(name=new_name, value=new_value, level_type=cluster[0].level_type, quality="Very Strong"))
                else:
                    merged.append(cluster[0])

                # Start a new cluster
                cluster = [level]

        # Process the last cluster
        if len(cluster) > 1:
            new_value = np.mean([l.value for l in cluster])
            base_names = set()
            for l in cluster:
                base_name = l.name.split(' ')[0]
                if 'Fibonacci' in base_name:
                    base_names.add('Fibonacci')
                elif 'Channel' in base_name:
                    base_names.add('Channel')
                elif 'Trend' in base_name:
                    base_names.add('Trend')
                else:
                    base_names.add('General')

            name_str = ', '.join(sorted(list(base_names)))
            new_name = f"Confluent Zone ({name_str})"
            merged.append(Level(name=new_name, value=new_value, level_type=cluster[0].level_type, quality="Very Strong"))
        elif cluster:
            merged.append(cluster[0])

        return merged
