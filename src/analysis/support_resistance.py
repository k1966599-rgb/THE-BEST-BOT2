import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base_analysis import BaseAnalysis
import logging
from .patterns.pattern_utils import get_pivots

logger = logging.getLogger(__name__)

class SupportResistanceAnalysis(BaseAnalysis):
    """
    Analyzes support and resistance levels, and demand/supply zones.
    """
    def __init__(self, config: dict = None, timeframe: str = '1h'):
        super().__init__(config, timeframe)
        overrides = self.config.get('TIMEFRAME_OVERRIDES', {}).get(self.timeframe, {})
        self.lookback = overrides.get('SR_LOOKBACK', self.config.get('SR_LOOKBACK', 200))
        self.cluster_percent = overrides.get('SR_CLUSTER_PERCENT', self.config.get('SR_CLUSTER_PERCENT', 0.5))
        self.min_touches = overrides.get('SR_MIN_TOUCHES', self.config.get('SR_MIN_TOUCHES', 2))
        self.zone_factor = overrides.get('SR_ZONE_FACTOR', self.config.get('SR_ZONE_FACTOR', 0.8)) # Percentage of ATR for zone height

    def _cluster_levels(self, levels: List[float]) -> List[float]:
        """
        Clusters a list of price levels to find significant S/R areas.
        """
        if not levels:
            return []

        levels.sort()
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            cluster_avg = np.mean(current_cluster)
            if (level - cluster_avg) / cluster_avg * 100 <= self.cluster_percent:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        clusters.append(np.mean(current_cluster))
        return clusters

    def _create_zones(self, levels: List[float], df: pd.DataFrame, zone_type: str) -> List[Dict[str, Any]]:
        """
        Creates demand or supply zones around the given S/R levels.
        """
        if 'ATR_14' not in df.columns:
            return []

        atr = df['ATR_14'].mean() * self.zone_factor
        zones = []

        for level in levels:
            zone_start = level - (atr / 2)
            zone_end = level + (atr / 2)

            touches = df[(df['low'] <= zone_end) & (df['high'] >= zone_start)]
            touch_count = len(touches)

            if touch_count >= self.min_touches:
                volume_in_zone = touches['volume'].sum()

                zones.append({
                    'start': zone_start,
                    'end': zone_end,
                    'level': level,
                    'touches': touch_count,
                    'volume': volume_in_zone,
                    'type': zone_type
                })
        return zones

    def _rate_zone_strength(self, zones: List[Dict[str, Any]], total_volume: float) -> List[Dict[str, Any]]:
        """
        Rates the strength of demand/supply zones.
        """
        if not zones:
            return []

        for zone in zones:
            touch_score = min(zone['touches'] / (self.min_touches * 2), 1.0)
            volume_score = min(zone['volume'] / (total_volume * 0.1), 1.0)
            total_strength = (touch_score * 0.6) + (volume_score * 0.4)

            if total_strength > 0.75:
                strength_text = "عالية"
            elif total_strength > 0.4:
                strength_text = "متوسطة"
            else:
                strength_text = "ضعيفة"

            zone['strength_score'] = total_strength
            zone['strength_text'] = strength_text

        return sorted(zones, key=lambda x: x['strength_score'], reverse=True)

    def _calculate_score(self, rated_zones: List[Dict], current_price: float, is_demand: bool) -> float:
        """
        Calculates the score for a set of zones.
        """
        score = 0
        if not rated_zones:
            return score

        closest_zone = min(rated_zones, key=lambda z: abs(z['level'] - current_price))
        distance_factor = 1 - min(abs(current_price - closest_zone['level']) / current_price, 1)

        score_modifier = 10 if is_demand else -10
        score += closest_zone['strength_score'] * score_modifier * distance_factor

        return score

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Identifies support, resistance, and demand/supply zones.
        """
        if len(df) < self.lookback:
            return {'error': 'Not enough data.', 'total_score': 0}

        data = df.tail(self.lookback)
        current_price = data['close'].iloc[-1]

        try:
            highs, lows = get_pivots(data)
            if not highs or not lows:
                return {'error': 'Could not find pivots.', 'total_score': 0}

            support_levels = self._cluster_levels([l['price'] for l in lows if l['price'] < current_price])
            resistance_levels = self._cluster_levels([h['price'] for h in highs if h['price'] > current_price])

            demand_zones = self._create_zones(support_levels, data, 'demand')
            supply_zones = self._create_zones(resistance_levels, data, 'supply')

            total_volume = data['volume'].sum()
            rated_demand_zones = self._rate_zone_strength(demand_zones, total_volume)
            rated_supply_zones = self._rate_zone_strength(supply_zones, total_volume)

            score = self._calculate_score(rated_demand_zones, current_price, is_demand=True)
            score += self._calculate_score(rated_supply_zones, current_price, is_demand=False)

            return {
                'supports': sorted([round(s, 4) for s in support_levels], reverse=True),
                'resistances': sorted([round(r, 4) for r in resistance_levels]),
                'all_demand_zones': rated_demand_zones,
                'all_supply_zones': rated_supply_zones,
                'total_score': round(score, 2)
            }

        except (ValueError, TypeError) as e:
            logger.exception("Error during S/R analysis")
            return {'error': str(e), 'total_score': 0}
