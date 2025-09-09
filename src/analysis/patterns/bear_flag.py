import pandas as pd
from typing import Dict, List
from datetime import datetime
from .base_pattern import BasePattern

class BearFlag(BasePattern):
    """
    A class for detecting the Bear Flag pattern.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float):
        super().__init__(df, config, highs, lows, current_price, price_tolerance)
        self.name = "Bear Flag"

    def check(self) -> List[Dict]:
        """
        Checks for the Bear Flag pattern.
        """
        for i in range(len(self.highs) - 2, max(-1, len(self.highs) - 10), -1):
            flagpole_start_high = self.highs[i]
            
            potential_poles = [l for l in self.lows if l['index'] > flagpole_start_high['index']]
            if not potential_poles:
                continue

            flagpole_end_low = min(potential_poles, key=lambda x: x['price'])
            flagpole_height = flagpole_start_high['price'] - flagpole_end_low['price']
            flagpole_duration = flagpole_end_low['index'] - flagpole_start_high['index']
            
            min_flagpole_height = self.df['close'].mean() * 0.03
            if flagpole_height < min_flagpole_height:
                continue
            
            flagpole_speed = flagpole_height / flagpole_duration if flagpole_duration > 0 else 0
            min_speed = self.df['close'].mean() * 0.001
            
            if flagpole_speed < min_speed:
                continue

            flag_highs = [h for h in self.highs if h['index'] > flagpole_end_low['index']]
            flag_lows = [l for l in self.lows if l['index'] > flagpole_end_low['index']]

            if len(flag_highs) < 2 or len(flag_lows) < 2:
                continue

            highest_retracement = max(flag_highs, key=lambda x: x['price'])
            retracement_level = (highest_retracement['price'] - flagpole_end_low['price']) / flagpole_height

            if retracement_level > 0.618:
                continue

            upper_trend, lower_trend = self._calculate_trend_lines(flag_highs, flag_lows)

            if upper_trend['slope'] < -flagpole_speed * 0.1 or lower_trend['slope'] < -flagpole_speed * 0.1:
                continue

            slope_difference = abs(upper_trend['slope'] - lower_trend['slope'])
            max_slope_diff = abs(upper_trend['slope'] * 0.5) if upper_trend['slope'] != 0 else 0.001

            if slope_difference > max_slope_diff:
                continue

            self._calculate_pattern_details(upper_trend, lower_trend, flagpole_start_high, flagpole_end_low, flagpole_height, flagpole_duration, flag_highs, flag_lows, retracement_level)
            break
        
        return self.found_patterns

    def _calculate_pattern_details(self, upper_trend, lower_trend, flagpole_start_high, flagpole_end_low, flagpole_height, flagpole_duration, flag_highs, flag_lows, retracement_level):
        resistance_current, support_current = self._get_current_levels(upper_trend, lower_trend)
        
        breakdown_occurred = self.current_price < support_current * (1 - self.price_tolerance * 0.5)
        false_breakout = self.current_price > resistance_current * (1 + self.price_tolerance * 0.5)
        
        if false_breakout:
            return
        
        status = "مكتمل ✅" if breakdown_occurred else "قيد التكوين 🟡"
        
        volume_analysis = self._analyze_volume(flag_highs, flag_lows, flagpole_start_high['index'])
        
        final_confidence = self._calculate_confidence(flagpole_height, retracement_level, upper_trend, lower_trend, flag_highs, flag_lows, volume_analysis, flagpole_duration, flag_lows[-1]['index'] - flagpole_end_low['index'] if flag_lows else 0)

        conservative_target = support_current - (flagpole_height * 0.8)
        aggressive_target = support_current - flagpole_height
        fibonacci_target = support_current - (flagpole_height * 1.618)
        
        stop_loss = resistance_current * 1.02
        risk_amount = abs(stop_loss - support_current)
        reward_amount = abs(support_current - conservative_target)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        pattern_strength = self._calculate_strength(flagpole_height, retracement_level, upper_trend, lower_trend, flag_highs, flag_lows, volume_analysis)

        pattern_info = {
            "name": "علم هابط (Bear Flag)",
            "status": status,
            "confidence": round(final_confidence, 1),
            "pattern_strength": round(pattern_strength, 1),
            "resistance_line": round(resistance_current, 6),
            "support_line": round(support_current, 6),
            "flagpole_start": round(flagpole_start_high['price'], 6),
            "flagpole_end": round(flagpole_end_low['price'], 6),
            "conservative_target": round(conservative_target, 6),
            "aggressive_target": round(aggressive_target, 6),
            "fibonacci_target": round(fibonacci_target, 6),
            "calculated_target": round(conservative_target, 6),
            "stop_loss": round(stop_loss, 6),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "flagpole_height": round(flagpole_height, 6),
            "retracement_level": round(retracement_level * 100, 1),
            "flagpole_duration": flagpole_duration,
            "flag_duration": flag_lows[-1]['index'] - flagpole_end_low['index'] if flag_lows else 0,
            "volume_analysis": volume_analysis,
            "time_identified": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.found_patterns.append(pattern_info)

    def _calculate_confidence(self, flagpole_height, retracement_level, upper_trend, lower_trend, flag_highs, flag_lows, volume_analysis, flagpole_duration, flag_duration) -> float:
        base_confidence = 70
        confidence_bonuses = 0
        confidence_bonuses += min(15, (flagpole_height / self.df['close'].mean()) * 200)
        if retracement_level < 0.382:
            confidence_bonuses += 10
        elif retracement_level < 0.5:
            confidence_bonuses += 5
        confidence_bonuses += min(10, (upper_trend['r_squared'] + lower_trend['r_squared']) * 5)
        confidence_bonuses += min(10, (len(flag_highs) + len(flag_lows) - 4) * 2)
        if volume_analysis and volume_analysis.get('volume_confirmation'):
            confidence_bonuses += 15
        if flagpole_duration * 0.5 <= flag_duration <= flagpole_duration * 2:
            confidence_bonuses += 5
        return min(95, base_confidence + confidence_bonuses)

    def _calculate_strength(self, flagpole_height, retracement_level, upper_trend, lower_trend, flag_highs, flag_lows, volume_analysis) -> float:
        pattern_strength = min(100, (
            (flagpole_height / self.df['close'].mean()) * 300 +
            (1 - retracement_level) * 30 +
            (upper_trend['r_squared'] + lower_trend['r_squared']) * 25 +
            len(flag_highs + flag_lows) * 3 +
            (15 if volume_analysis.get('volume_confirmation', False) else 0)
        ))
        return pattern_strength
