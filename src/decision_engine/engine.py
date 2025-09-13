import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from .trade_setup import TradeSetup
from ..analysis.data_models import Pattern, Level

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Processes analysis results to generate trading recommendations."""
    def __init__(self, config: dict):
        self.config = config.get('recommendation', {})
        if not self.config:
            logger.warning("Recommendation config not found. Using empty defaults.")
            self.config = {}

    def make_recommendation(self, analysis_results: Dict[str, Any], df: pd.DataFrame, symbol: str, timeframe: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
        logger.info(f"Decision Engine: Making recommendation for {symbol} on {timeframe}.")

        patterns: List[Pattern] = analysis_results.get('patterns', [])
        main_action = "Wait ⏳"
        confidence = 50
        trade_setup = None

        if patterns:
            primary_pattern = patterns[0]
            if 'Bullish' in primary_pattern.name or 'Bottom' in primary_pattern.name:
                main_action = "Buy 📈"
            elif 'Bearish' in primary_pattern.name or 'Top' in primary_pattern.name:
                main_action = "Sell 📉"

            if primary_pattern.status == 'Forming' or primary_pattern.confidence < 65:
                main_action = "Wait ⏳"
            confidence = primary_pattern.confidence

            if chat_id:
                try:
                    confirmation_conditions, optional_conditions = self._generate_confirmation_conditions(df, analysis_results, primary_pattern)
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
                        target3=primary_pattern.target3,
                        confirmation_rule='3_candle_close',
                        confirmation_conditions=confirmation_conditions,
                        optional_confirmation_conditions=optional_conditions,
                        raw_pattern_data=primary_pattern.__dict__
                    )
                except Exception as e:
                    logger.exception(f"Failed to create TradeSetup from pattern: {e}")

        conflict_note = None
        trend_direction = analysis_results.get('other_analysis', {}).get('TrendAnalysis', {}).get('trend_direction')

        if trend_direction:
            is_bullish_action = 'Buy' in main_action
            is_bearish_action = 'Sell' in main_action
            if is_bullish_action and trend_direction == 'Downtrend':
                conflict_note = "Bullish pattern conflicts with the bearish overall trend."
                main_action = "Wait ⏳"
            if is_bearish_action and trend_direction == 'Uptrend':
                conflict_note = "Bearish pattern conflicts with the bullish overall trend."
                main_action = "Wait ⏳"

        total_score = confidence if 'Buy' in main_action else -confidence if 'Sell' in main_action else 0

        return {
            'symbol': symbol, 'timeframe': timeframe, 'main_action': main_action,
            'confidence': confidence, 'total_score': total_score, 'conflict_note': conflict_note,
            'raw_analysis': analysis_results, 'trade_setup': trade_setup
        }

    def _generate_confirmation_conditions(self, df: pd.DataFrame, analysis: Dict[str, Any], pattern: Pattern) -> (List[str], List[str]):
        is_bullish = 'Bullish' in pattern.name or 'Bottom' in pattern.name

        main_conditions = []
        breakout_direction = "above" if is_bullish else "below"
        main_conditions.append(f"إغلاق 3 شموع {pattern.timeframe} متتالية {breakout_direction} مستوى ${pattern.activation_level:,.2f}")

        optional_conditions = []
        if 'obv' in df.columns:
            if df['obv'].iloc[-1] > df['obv'].iloc[-2]:
                optional_conditions.append("OBV متزايد أثناء الاختراق أو بعده.")

        if 'macd_12_26_9' in df.columns and 'macdh_12_26_9' in df.columns and 'macds_12_26_9' in df.columns:
            macd_line = df['macd_12_26_9'].iloc[-1]
            signal_line = df['macds_12_26_9'].iloc[-1]
            if is_bullish and macd_line > signal_line:
                optional_conditions.append("MACD إيجابي (خط الماكد فوق خط الإشارة).")
            elif not is_bullish and macd_line < signal_line:
                 optional_conditions.append("MACD سلبي (خط الماكد تحت خط الإشارة).")

        if 'adx_14' in df.columns:
            adx_value = df['adx_14'].iloc[-1]
            if adx_value > 25:
                optional_conditions.append(f"ADX > 25 (قوة في الاتجاه الحالي).")

        if 'atrp_14' in df.columns:
             if df['atrp_14'].iloc[-1] > df['atrp_14'].iloc[-5:].mean():
                 optional_conditions.append("ATR مرتفع أو في تصاعد (قوة في الحركة).")

        return main_conditions, optional_conditions

    def rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info(f"Decision Engine: Ranking {len(recommendations)} recommendations.")

        for rec in recommendations:
            if not rec.get('error'):
                signal_multiplier = 0.1 if 'Wait' in rec.get('main_action', '') else 1.0
                rank_score = abs(rec.get('total_score', 0)) * signal_multiplier
                rec['rank_score'] = rank_score
            else:
                rec['rank_score'] = -1

        return sorted(recommendations, key=lambda x: x.get('rank_score', -1), reverse=True)
