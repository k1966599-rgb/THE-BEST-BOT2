import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from .trade_setup import TradeSetup

logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    The DecisionEngine centralizes the logic for interpreting analysis results
    and making a final trading recommendation.
    """
    def __init__(self, config: dict):
        """
        Initializes the Decision Engine with the application's configuration.

        :param config: A dictionary containing recommendation weights, thresholds, etc.
        """
        self.config = config.get('recommendation', {})
        if not self.config:
            logger.warning("Recommendation config not found. Using empty defaults.")
            self.config = {}

    def _get_score_from_result(self, result_key: str, result_data: dict) -> float:
        """
        Extracts a score from a result dictionary, handling various possible key names.
        This makes the system more robust to changes in analysis modules.
        """
        # Search for any key that ends with '_score' or is 'total_score'
        if 'total_score' in result_data:
            return result_data['total_score']

        for key in result_data.keys():
            if key.endswith('_score'):
                return result_data[key]

        logger.warning(f"Could not find a score key in result for '{result_key}'. Defaulting to 0.")
        return 0.0

    def make_recommendation(self, analysis_results: Dict[str, Any], df: pd.DataFrame, symbol: str, timeframe: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculates a final recommendation based on the collected analysis results.
        This encapsulates the logic from the old `calculate_final_recommendation`.
        """
        logger.info(f"Decision Engine: Making recommendation for {symbol} on {timeframe}.")
        analysis_results['df'] = df

        # --- 1. Calculate Weighted Score ---
        scores = {
            key: self._get_score_from_result(key, data)
            for key, data in analysis_results.items()
            if isinstance(data, dict)
        }

        weights = self.config.get('SCORE_WEIGHTS', {})
        # Map class names to the keys used in the config's SCORE_WEIGHTS
        key_map = {
            'TechnicalIndicators': 'indicators',
            'TrendAnalysis': 'trends',
            'PriceChannels': 'channels',
            'SupportResistanceAnalysis': 'support_resistance',
            'FibonacciAnalysis': 'fibonacci',
            'ClassicPatterns': 'patterns',
            'TrendLineAnalysis': 'trend_lines'
        }

        total_score = 0
        for class_name, score in scores.items():
            weight_key = key_map.get(class_name)
            if weight_key:
                weight = weights.get(weight_key, 0)
                total_score += score * weight
            else:
                logger.warning(f"No weight key mapping found for analysis module: {class_name}")

        # --- 2. Determine Initial Action based on Score ---
        thresholds = self.config.get('THRESHOLDS', {})
        actions = self.config.get('ACTIONS', {})
        confidences = self.config.get('CONFIDENCE_LEVELS', {})

        if total_score >= thresholds.get('strong_buy', 20):
            action_key = 'strong_buy'
        elif total_score >= thresholds.get('buy', 10):
            action_key = 'buy'
        elif total_score >= thresholds.get('hold', -5):
            action_key = 'hold'
        elif total_score >= thresholds.get('sell', -15):
            action_key = 'sell'
        else:
            action_key = 'strong_sell'

        # Store the initial action before checking for conflicts
        initial_action = actions.get(action_key, "انتظار ⏳")
        main_action = initial_action
        confidence = confidences.get(action_key, 60)

        # --- 3. Resolve Contradictions with Chart Patterns ---
        conflict_note = None
        patterns_result = analysis_results.get('ClassicPatterns', {})
        found_patterns = patterns_result.get('found_patterns', [])

        if found_patterns:
            p = found_patterns[0]
            is_bullish_pattern = 'صاعد' in p.get('name', '') or 'قاع' in p.get('name', '')
            is_bearish_action_initial = 'بيع' in initial_action

            if is_bullish_pattern and is_bearish_action_initial and 'قيد التكوين' in p.get('status', ''):
                main_action = actions.get('hold', "انتظار ⏳")
                confidence = p.get('confidence', 70)
                conflict_note = self.config.get('CONFLICT_NOTE_TEMPLATE', "").format(
                    original_action=initial_action, new_action=main_action,
                    pattern_type="إيجابي", pattern_name=p.get('name')
                )

            is_bearish_pattern = 'هابط' in p.get('name', '') or 'قمة' in p.get('name', '')
            is_bullish_action_initial = 'شراء' in initial_action
            if is_bearish_pattern and is_bullish_action_initial and 'قيد التكوين' in p.get('status', ''):
                main_action = actions.get('hold', "انتظار ⏳")
                confidence = p.get('confidence', 70)
                conflict_note = self.config.get('CONFLICT_NOTE_TEMPLATE', "").format(
                    original_action=initial_action, new_action=main_action,
                    pattern_type="سلبي", pattern_name=p.get('name')
                )

        logger.info(f"Recommendation: {main_action} with score {total_score:.2f} and confidence {confidence}%.")

        # --- 4. Create TradeSetup if a pattern exists and we have a chat_id ---
        trade_setup: Optional[TradeSetup] = None
        if found_patterns and chat_id:
            p = found_patterns[0]
            try:
                trade_setup = TradeSetup(
                    chat_id=chat_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    pattern_name=p.get('name', 'N/A'),
                    pattern_status=p.get('status', 'مكتمل'),
                    entry_price=p.get('activation_level', 0),
                    stop_loss=p.get('stop_loss', 0),
                    target1=p.get('price_target', 0),
                    raw_pattern_data=p
                )
            except Exception:
                logger.exception("Failed to create TradeSetup from pattern data.")


        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'main_action': main_action,
            'confidence': confidence,
            'total_score': total_score,
            'individual_scores': scores,
            'conflict_note': conflict_note,
            'raw_analysis': analysis_results,
            'trade_setup': trade_setup
        }

    def rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks a list of recommendations from different timeframes, prioritizing
        actionable signals and those with strong indicators like divergences.
        This encapsulates the logic from the old `rank_opportunities`.
        """
        logger.info(f"Decision Engine: Ranking {len(recommendations)} recommendations.")

        for rec in recommendations:
            if not rec.get('error'):
                # Give a significant penalty to "Wait" signals
                signal_multiplier = 0.1 if 'انتظار' in rec.get('main_action', '') else 1.0

                # Add a bonus for divergences, as they are strong signals
                divergence_bonus = 1.0
                # The raw analysis results are needed to check for divergences
                indicators_analysis = rec.get('raw_analysis', {}).get('TechnicalIndicators', {})
                if indicators_analysis.get('rsi_divergence') or indicators_analysis.get('macd_divergence'):
                    divergence_bonus = 1.2  # 20% bonus

                rank_score = abs(rec.get('total_score', 0)) * (rec.get('confidence', 0) / 100) * signal_multiplier * divergence_bonus
                rec['rank_score'] = rank_score
            else:
                rec['rank_score'] = -1

        return sorted(recommendations, key=lambda x: x.get('rank_score', -1), reverse=True)
