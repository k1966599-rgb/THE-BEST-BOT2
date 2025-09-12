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

        if patterns:
            primary_pattern = patterns[0]
            if 'صاعد' in primary_pattern.name or 'قاع' in primary_pattern.name:
                main_action = "شراء 📈"
            elif 'هابط' in primary_pattern.name or 'قمة' in primary_pattern.name:
                main_action = "بيع 📉"

            if primary_pattern.status == 'قيد التكوين' or primary_pattern.confidence < 65:
                main_action = "انتظار ⏳"

            confidence = primary_pattern.confidence

            if chat_id:
                try:
                    confirmation_conditions = self._generate_confirmation_conditions(df, analysis_results, primary_pattern)
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

        if main_action == "انتظار ⏳":
            trade_setup = None

        total_score = confidence if 'شراء' in main_action else -confidence if 'بيع' in main_action else 0

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'main_action': main_action,
            'confidence': confidence,
            'total_score': total_score,
            'conflict_note': conflict_note,
            'raw_analysis': analysis_results,
            'trade_setup': trade_setup
        }

    def _confirm_breakout_volume(self, df: pd.DataFrame) -> Optional[str]:
        """Checks if the volume on the last candle is significantly higher than average."""
        if 'volume' not in df.columns or len(df) < 21:
            return None
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-2]
        last_volume = df['volume'].iloc[-1]
        if last_volume > avg_volume * 1.5:
            return "✅ حجم تداول مرتفع عند الاختراق يؤكد الزخم."
        return None

    def _confirm_ma_support_resistance(self, df: pd.DataFrame, is_bullish: bool) -> Optional[str]:
        """Checks if the price is respecting key moving averages."""
        if 'sma_20' not in df.columns or 'sma_50' not in df.columns:
            return None
        last_close = df['close'].iloc[-1]
        if is_bullish and last_close > df['sma_20'].iloc[-1] and last_close > df['sma_50'].iloc[-1]:
            return "✅ السعر يتداول فوق المتوسطات المتحركة الرئيسية (20, 50)."
        if not is_bullish and last_close < df['sma_20'].iloc[-1] and last_close < df['sma_50'].iloc[-1]:
            return "✅ السعر يتداول تحت المتوسطات المتحركة الرئيسية (20, 50)."
        return None

    def _confirm_trend_alignment(self, analysis: Dict[str, Any], is_bullish: bool) -> Optional[str]:
        """Checks if the trade direction aligns with the overall trend."""
        trend = analysis.get('other_analysis', {}).get('TrendAnalysis', {})
        trend_direction = trend.get('trend_direction')
        if is_bullish and trend_direction == 'Uptrend':
            return f"✅ الصفقة تتوافق مع الاتجاه العام الصاعد (ثقة {trend.get('confidence', 0):.0f}%)."
        if not is_bullish and trend_direction == 'Downtrend':
            return f"✅ الصفقة تتوافق مع الاتجاه العام الهابط (ثقة {trend.get('confidence', 0):.0f}%)."
        return None

    def _generate_confirmation_conditions(self, df: pd.DataFrame, analysis: Dict[str, Any], pattern: Pattern) -> List[str]:
        """
        Generates a list of dynamic, intelligent confirmation conditions for a trade setup.
        """
        is_bullish = 'صاعد' in pattern.name or 'قاع' in pattern.name
        conditions = []

        breakout_direction = "فوق" if is_bullish else "تحت"
        conditions.append(f"⏳ إغلاق شمعة {pattern.timeframe} {breakout_direction} مستوى {pattern.activation_level:,.2f}")

        confirmation_checks = [
            self._confirm_breakout_volume(df),
            self._confirm_ma_support_resistance(df, is_bullish),
            self._confirm_trend_alignment(analysis, is_bullish)
        ]

        for confirmation in confirmation_checks:
            if confirmation:
                conditions.append(confirmation)

        if len(conditions) == 1:
            conditions.append("⚠️ لا توجد تأكيدات قوية، يرجى توخي الحذر.")

        return conditions

    def rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks recommendations based on score and confidence.
        """
        logger.info(f"Decision Engine: Ranking {len(recommendations)} recommendations.")

        for rec in recommendations:
            if not rec.get('error'):
                signal_multiplier = 0.1 if 'انتظار' in rec.get('main_action', '') else 1.0
                rank_score = abs(rec.get('total_score', 0)) * signal_multiplier
                rec['rank_score'] = rank_score
            else:
                rec['rank_score'] = -1

        return sorted(recommendations, key=lambda x: x.get('rank_score', -1), reverse=True)
