import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from .base_pattern import BasePattern

class RisingWedge(BasePattern):
    """
    A class for detecting the Rising Wedge pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Rising Wedge"

    def check(self) -> List[Dict]:
        """
        Checks for the Rising Wedge pattern.
        """
        window_highs, window_lows = self._filter_pivots(search_window_bars=80)

        if len(window_highs) < 3 or len(window_lows) < 3:
            return []

        upper_trend, lower_trend = self._calculate_trend_lines(window_highs, window_lows)

        if self._is_valid_wedge(upper_trend, lower_trend):
            self._calculate_pattern_details(upper_trend, lower_trend, window_highs, window_lows)

        return self.found_patterns

    def _is_valid_wedge(self, upper_trend: Dict, lower_trend: Dict) -> bool:
        """
        Checks if the trend lines form a valid rising wedge.
        """
        # Both lines must be upward sloping
        if upper_trend['slope'] <= 0 or lower_trend['slope'] <= 0:
            return False

        # Lower trend line must be steeper than the upper one (convergence)
        if lower_trend['slope'] <= upper_trend['slope']:
            return False

        # Trend lines must have a good fit
        if upper_trend['r_squared'] < 0.6 or lower_trend['r_squared'] < 0.6:
            return False

        return True

    def _calculate_pattern_details(self, upper_trend: Dict, lower_trend: Dict, window_highs: List[Dict], window_lows: List[Dict]):
        """
        Calculates the details of the pattern and adds it to the list of found patterns.
        """
        resistance_current, support_current = self._get_current_levels(upper_trend, lower_trend)
        current_index = len(self.df) - 1

        if self.current_price > resistance_current * (1 + self.price_tolerance):
            return  # Early breakout, pattern might not complete

        if abs(lower_trend['slope'] - upper_trend['slope']) < 1e-10:
            return # Parallel lines

        convergence_x = (upper_trend['intercept'] - lower_trend['intercept']) / (lower_trend['slope'] - upper_trend['slope'])
        if convergence_x <= current_index:
            return # Convergence in the past

        breakdown_occurred = self.current_price < support_current * (1 - self.price_tolerance * 0.5)
        status = "مكتمل ✅" if breakdown_occurred else "قيد التكوين 🟡"

        wedge_start_index = min([p['index'] for p in window_highs + window_lows])
        resistance_start = upper_trend['slope'] * wedge_start_index + upper_trend['intercept']
        support_start = lower_trend['slope'] * wedge_start_index + lower_trend['intercept']

        initial_width = resistance_start - support_start
        current_width = resistance_current - support_current
        compression_ratio = 1 - (current_width / initial_width) if initial_width > 0 else 0

        momentum_analysis = self._analyze_momentum()
        volume_analysis = self._analyze_volume(window_highs, window_lows, wedge_start_index)

        final_confidence = self._calculate_confidence(upper_trend, lower_trend, window_highs, window_lows, compression_ratio, convergence_x, volume_analysis, momentum_analysis)

        pattern_strength = self._calculate_strength(upper_trend, lower_trend, window_highs, window_lows, compression_ratio, volume_analysis, momentum_analysis)

        wedge_height = max([p['price'] for p in window_highs]) - min([p['price'] for p in window_lows])

        conservative_target = support_current - (wedge_height * 0.6)
        aggressive_target = support_current - wedge_height
        fibonacci_target = support_current - (wedge_height * 1.618)

        stop_loss = resistance_current * 1.02
        risk_amount = abs(stop_loss - support_current)
        reward_amount = abs(support_current - conservative_target)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        pattern_duration = current_index - wedge_start_index
        wedge_maturity = compression_ratio * 100

        if wedge_maturity < 30:
            maturity_stage = "مبكر"
        elif wedge_maturity < 70:
            maturity_stage = "متوسط"
        else:
            maturity_stage = "متأخر"

        pattern_info = {
            "name": "وتد صاعد (Rising Wedge)",
            "status": status,
            "confidence": round(final_confidence, 1),
            "pattern_strength": round(pattern_strength, 1),
            "resistance_line": round(resistance_current, 6),
            "support_line": round(support_current, 6),
            "upper_slope": round(upper_trend['slope'], 8),
            "lower_slope": round(lower_trend['slope'], 8),
            "conservative_target": round(conservative_target, 6),
            "aggressive_target": round(aggressive_target, 6),
            "fibonacci_target": round(fibonacci_target, 6),
            "calculated_target": round(conservative_target, 6),
            "stop_loss": round(stop_loss, 6),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "wedge_height": round(wedge_height, 6),
            "initial_width": round(initial_width, 6),
            "current_width": round(current_width, 6),
            "compression_ratio": round(compression_ratio * 100, 1),
            "convergence_distance": round(convergence_x - current_index, 1),
            "pattern_duration": pattern_duration,
            "upper_trendline_quality": round(upper_trend['r_squared'], 3),
            "lower_trendline_quality": round(lower_trend['r_squared'], 3),
            "volume_analysis": volume_analysis,
            "momentum_analysis": momentum_analysis,
            "entry_signal": 'كسر الدعم' if not breakdown_occurred else 'دخل بالفعل',
            "timeframe_suitability": 'ممتاز' if 20 <= pattern_duration <= 70 else 'جيد',
            "wedge_maturity": round(wedge_maturity, 1),
            "maturity_stage": maturity_stage,
            "time_identified": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.found_patterns.append(pattern_info)

    def _analyze_momentum(self) -> Dict:
        """
        Analyzes the momentum for the pattern.
        """
        momentum_analysis = {}
        if len(self.df) >= 20:
            early_momentum = self.df['close'].iloc[-20:-15].pct_change().mean() if len(self.df) >= 20 else 0
            recent_momentum = self.df['close'].iloc[-5:].pct_change().mean()

            momentum_analysis = {
                'early_momentum': early_momentum,
                'recent_momentum': recent_momentum,
                'momentum_divergence': early_momentum > recent_momentum and early_momentum > 0,
                'momentum_weakening': abs(recent_momentum) < abs(early_momentum) * 0.7
            }
        return momentum_analysis

    def _calculate_confidence(self, upper_trend, lower_trend, window_highs, window_lows, compression_ratio, convergence_x, volume_analysis, momentum_analysis) -> float:
        base_confidence = 65
        confidence_bonuses = 0
        confidence_bonuses += min(20, (upper_trend['r_squared'] + lower_trend['r_squared']) * 10)
        confidence_bonuses += min(15, compression_ratio * 30)
        confidence_bonuses += min(15, (len(window_highs) + len(window_lows)) * 1.5)
        convergence_strength = abs(lower_trend['slope'] - upper_trend['slope']) / abs(upper_trend['slope'])
        confidence_bonuses += min(10, convergence_strength * 20)
        if volume_analysis and volume_analysis['volume_decline']:
            confidence_bonuses += 10
        if momentum_analysis and momentum_analysis['momentum_divergence']:
            confidence_bonuses += 15
        distance_to_convergence = convergence_x - len(self.df) + 1
        if 5 <= distance_to_convergence <= 30:
            confidence_bonuses += 10
        elif distance_to_convergence > 50:
            confidence_bonuses -= 5
        return min(95, base_confidence + confidence_bonuses)

    def _calculate_strength(self, upper_trend, lower_trend, window_highs, window_lows, compression_ratio, volume_analysis, momentum_analysis) -> float:
        convergence_strength = abs(lower_trend['slope'] - upper_trend['slope']) / abs(upper_trend['slope'])
        pattern_strength = min(100, (
            (upper_trend['r_squared'] + lower_trend['r_squared']) * 25 +
            compression_ratio * 30 +
            len(window_highs + window_lows) * 2 +
            convergence_strength * 15 +
            (10 if volume_analysis.get('volume_decline', False) else 0) +
            (15 if momentum_analysis.get('momentum_divergence', False) else 0)
        ))
        return pattern_strength
