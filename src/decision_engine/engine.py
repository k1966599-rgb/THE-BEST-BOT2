import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from .trade_setup import TradeSetup
from ..analysis.data_models import Pattern, Level

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self, config: dict):
        self.config = config.get('recommendation', {})
        if not self.config:
            logger.warning("Recommendation config not found. Using empty defaults.")
            self.config = {}

    def make_recommendation(self, analysis_results: Dict[str, Any], df: pd.DataFrame, symbol: str, timeframe: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
        logger.info(f"Decision Engine: Making recommendation for {symbol} on {timeframe}.")

        patterns: List[Pattern] = analysis_results.get('patterns', [])
        main_action = "انتظار ⏳"
        confidence = 50
        trade_setup = None

        # --- 1. Base decision on the most relevant pattern found ---
        if patterns:
            primary_pattern = patterns[0] # Assuming orchestrator sorts them by relevance

            # Determine action from pattern type
            if 'صاعد' in primary_pattern.name or 'قاع' in primary_pattern.name:
                main_action = "شراء 📈"
            elif 'هابط' in primary_pattern.name or 'قمة' in primary_pattern.name:
                main_action = "بيع 📉"

            # If pattern is not yet active, or confidence is too low, recommend waiting
            if primary_pattern.status == 'قيد التكوين' or primary_pattern.confidence < 65:
                main_action = "انتظار ⏳"

            confidence = primary_pattern.confidence

            # --- 2. Create TradeSetup from Pattern ---
            if chat_id:
                try:
                    confirmation_conditions = self._generate_confirmation_conditions(analysis_results, primary_pattern)
                    trade_setup = TradeSetup(
                        chat_id=chat_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern_name=primary_pattern.name,
                        pattern_status=primary_pattern.status,
                        entry_price=primary_pattern.activation_level,
                        stop_loss=primary_pattern.invalidation_level,
                        target1=primary_pattern.target1,
                        target2=primary_pattern.target2,
                        confirmation_conditions=confirmation_conditions,
                        raw_pattern_data=primary_pattern.__dict__
                    )
                except Exception as e:
                    logger.exception(f"Failed to create TradeSetup from pattern: {e}")

        # --- 3. Conflict Resolution with General Trend ---
        conflict_note = None
        trend_direction = analysis_results.get('other_analysis', {}).get('TrendAnalysis', {}).get('trend_direction')

        if trend_direction:
            is_bullish_action = 'شراء' in main_action
            is_bearish_action = 'بيع' in main_action

            if is_bullish_action and trend_direction == 'Downtrend':
                conflict_note = "النمط الصاعد يتعارض مع الاتجاه العام الهابط. يوصى بانتظار تأكيد قوي."
                main_action = "انتظار ⏳"

            if is_bearish_action and trend_direction == 'Uptrend':
                conflict_note = "النمط الهابط يتعارض مع الاتجاه العام الصاعد. يوصى بانتظار تأكيد قوي."
                main_action = "انتظار ⏳"

        # --- 4. Final Sanity Check ---
        # If, after all logic, the recommendation is to wait, there should be no active trade setup.
        if main_action == "انتظار ⏳":
            trade_setup = None

        # Simplified score for ranking
        total_score = confidence if 'شراء' in main_action else -confidence if 'بيع' in main_action else 0

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'main_action': main_action,
            'confidence': confidence,
            'total_score': total_score,
            'conflict_note': conflict_note,
            'raw_analysis': analysis_results, # Pass the full analysis for reporting
            'trade_setup': trade_setup
        }

    def _generate_confirmation_conditions(self, analysis: Dict[str, Any], pattern: Pattern) -> List[str]:
        """
        Generates a list of dynamic confirmation conditions for a trade setup.
        """
        conditions = [f"إغلاق شمعة {pattern.timeframe} فوق مستوى {pattern.activation_level:,.2f}"]

        # Add volume confirmation
        conditions.append("تزايد حجم التداول عند الاختراق")

        # Add indicator confirmation
        # This part can be expanded greatly. For now, a simple placeholder.
        other_analysis = analysis.get('other_analysis', {})
        if 'TechnicalIndicators' in other_analysis:
             conditions.append("مؤشرات فنية إيجابية (RSI > 50)")

        # Add support confirmation
        supports: List[Level] = analysis.get('supports', [])
        for s in supports:
            if "فيبو 0.618" in s.name:
                conditions.append(f"الارتداد من دعم فيبوناتشي القوي عند ${s.value:,.2f}")
                break # Add only one fib support condition

        return conditions

    def rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks recommendations based on score and confidence.
        """
        logger.info(f"Decision Engine: Ranking {len(recommendations)} recommendations.")

        for rec in recommendations:
            if not rec.get('error'):
                # Simple ranking: prioritize actionable signals with high confidence
                signal_multiplier = 0.1 if 'انتظار' in rec.get('main_action', '') else 1.0
                rank_score = abs(rec.get('total_score', 0)) * signal_multiplier
                rec['rank_score'] = rank_score
            else:
                rec['rank_score'] = -1

        return sorted(recommendations, key=lambda x: x.get('rank_score', -1), reverse=True)
