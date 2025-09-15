import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
from src.indicators.indicators import apply_all_indicators
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

        for pattern in master_patterns:
            if pattern.target1:
                master_resistances.append(Level(
                    name="pattern target",
                    value=pattern.target1,
                    level_type='resistance',
                    quality='Target'
                ))

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
                if len(cluster) > 1:
                    new_value = np.mean([l.value for l in cluster])
                    min_val = min(l.value for l in cluster)
                    max_val = max(l.value for l in cluster)

                    # Prioritize the name of the level with the highest quality in the cluster
                    cluster.sort(key=lambda x: x.quality or '', reverse=True)
                    new_name = f"Confluent Zone: {cluster[0].name}"

                    merged.append(Level(
                        name=new_name,
                        value=new_value,
                        level_type=cluster[0].level_type,
                        quality="Very Strong",
                        raw_data={'range_min': min_val, 'range_max': max_val}
                    ))
                else:
                    merged.append(cluster[0])

                cluster = [level]

        if len(cluster) > 1:
            new_value = np.mean([l.value for l in cluster])
            min_val = min(l.value for l in cluster)
            max_val = max(l.value for l in cluster)

            # Prioritize the name of the level with the highest quality in the cluster
            cluster.sort(key=lambda x: x.quality or '', reverse=True)
            new_name = f"Confluent Zone: {cluster[0].name}"

            merged.append(Level(
                name=new_name,
                value=new_value,
                level_type=cluster[0].level_type,
                quality="Very Strong",
                raw_data={'range_min': min_val, 'range_max': max_val}
            ))
        elif cluster:
            merged.append(cluster[0])

        return merged
