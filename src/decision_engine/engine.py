import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from .trade_setup import TradeSetup
from ..analysis.data_models import Pattern, Level

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Processes analysis results to generate trading recommendations.

    This engine takes the raw output from the analysis orchestrator,
    interprets the patterns and indicators, checks for conflicts, and
    formulates a clear trading recommendation (Buy, Sell, Wait). It can also
    generate a detailed `TradeSetup` object for monitoring.
    """
    def __init__(self, config: dict):
        """Initializes the DecisionEngine.

        Args:
            config (dict): The main configuration dictionary, from which the
                'recommendation' section will be used.
        """
        self.config = config.get('recommendation', {})
        if not self.config:
            logger.warning("Recommendation config not found. Using empty defaults.")
            self.config = {}

    def make_recommendation(self, analysis_results: Dict[str, Any], df: pd.DataFrame, symbol: str, timeframe: str, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """Makes a trading recommendation based on analysis results.

        The logic prioritizes detected patterns but will check for conflicts
        with the overall market trend. If a valid, non-conflicting trade
        opportunity is found, it may generate a TradeSetup object.

        Args:
            analysis_results (Dict[str, Any]): The aggregated results from the
                AnalysisOrchestrator.
            df (pd.DataFrame): The DataFrame with market data.
            symbol (str): The trading symbol.
            timeframe (str): The timeframe of the analysis.
            chat_id (Optional[int], optional): The chat ID for which to create
                a TradeSetup. If None, no TradeSetup is created. Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing the recommendation,
            including 'main_action', 'confidence', and an optional
            'trade_setup'.
        """
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
            is_bullish_action = 'Buy' in main_action
            is_bearish_action = 'Sell' in main_action
            if is_bullish_action and trend_direction == 'Downtrend':
                conflict_note = "Bullish pattern conflicts with the bearish overall trend. Strong confirmation is recommended."
                main_action = "Wait ⏳"
            if is_bearish_action and trend_direction == 'Uptrend':
                conflict_note = "Bearish pattern conflicts with the bullish overall trend. Strong confirmation is recommended."
                main_action = "Wait ⏳"

        # This was the root cause of the user's complaint.
        # A trade setup should be presented if a pattern is found, even if the
        # final recommendation is to "Wait", so the user can evaluate it.
        # if main_action == "Wait ⏳":
        #     trade_setup = None

        total_score = confidence if 'Buy' in main_action else -confidence if 'Sell' in main_action else 0

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
        """Checks for high volume on the most recent candle.

        Args:
            df (pd.DataFrame): The market data DataFrame.

        Returns:
            Optional[str]: A confirmation message if volume is high,
            otherwise None.
        """
        if 'volume' not in df.columns or len(df) < 21:
            return None
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-2]
        last_volume = df['volume'].iloc[-1]
        if last_volume > avg_volume * 1.5:
            return "✅ High breakout volume confirms momentum."
        return None

    def _confirm_ma_support_resistance(self, df: pd.DataFrame, is_bullish: bool) -> Optional[str]:
        """Checks if price is trading above/below key moving averages.

        Args:
            df (pd.DataFrame): The market data DataFrame.
            is_bullish (bool): True if checking for a bullish setup, False otherwise.

        Returns:
            Optional[str]: A confirmation message if the condition is met,
            otherwise None.
        """
        if 'sma_20' not in df.columns or 'sma_50' not in df.columns:
            return None
        last_close = df['close'].iloc[-1]
        if is_bullish and last_close > df['sma_20'].iloc[-1] and last_close > df['sma_50'].iloc[-1]:
            return "✅ Price is trading above key moving averages (20, 50)."
        if not is_bullish and last_close < df['sma_20'].iloc[-1] and last_close < df['sma_50'].iloc[-1]:
            return "✅ Price is trading below key moving averages (20, 50)."
        return None

    def _confirm_trend_alignment(self, analysis: Dict[str, Any], is_bullish: bool) -> Optional[str]:
        """Checks if the trade direction aligns with the overall trend.

        Args:
            analysis (Dict[str, Any]): The analysis results dictionary.
            is_bullish (bool): True if checking for a bullish setup.

        Returns:
            Optional[str]: A confirmation message if the trade aligns with
            the trend, otherwise None.
        """
        trend = analysis.get('other_analysis', {}).get('TrendAnalysis', {})
        trend_direction = trend.get('trend_direction')
        if is_bullish and trend_direction == 'Uptrend':
            return f"✅ Trade aligns with the bullish overall trend (Confidence: {trend.get('confidence', 0):.0f}%)."
        if not is_bullish and trend_direction == 'Downtrend':
            return f"✅ Trade aligns with the bearish overall trend (Confidence: {trend.get('confidence', 0):.0f}%)."
        return None

    def _generate_confirmation_conditions(self, df: pd.DataFrame, analysis: Dict[str, Any], pattern: Pattern) -> List[str]:
        """Generates a list of confirmation conditions for a trade setup.

        This method aggregates results from various confirmation checks to
        provide a human-readable list of conditions that would strengthen
        the case for a trade.

        Args:
            df (pd.DataFrame): The market data DataFrame.
            analysis (Dict[str, Any]): The analysis results.
            pattern (Pattern): The detected pattern object.

        Returns:
            List[str]: A list of string messages for the user.
        """
        is_bullish = 'Bullish' in pattern.name or 'Bottom' in pattern.name
        conditions = []

        breakout_direction = "above" if is_bullish else "below"
        conditions.append(f"⏳ Close a {pattern.timeframe} candle {breakout_direction} the {pattern.activation_level:,.2f} level")

        confirmation_checks = [
            self._confirm_breakout_volume(df),
            self._confirm_ma_support_resistance(df, is_bullish),
            self._confirm_trend_alignment(analysis, is_bullish)
        ]

        for confirmation in confirmation_checks:
            if confirmation:
                conditions.append(confirmation)

        if len(conditions) == 1:
            conditions.append("⚠️ No strong confirmations, please be cautious.")

        return conditions

    def rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranks a list of recommendations based on a calculated score.

        The ranking score is based on the recommendation's total score and
        is weighted down if the main action is 'Wait'.

        Args:
            recommendations (List[Dict[str, Any]]): A list of recommendation
                dictionaries to be ranked.

        Returns:
            List[Dict[str, Any]]: The list of recommendations, sorted in
            descending order of their rank score.
        """
        logger.info(f"Decision Engine: Ranking {len(recommendations)} recommendations.")

        for rec in recommendations:
            if not rec.get('error'):
                signal_multiplier = 0.1 if 'Wait' in rec.get('main_action', '') else 1.0
                rank_score = abs(rec.get('total_score', 0)) * signal_multiplier
                rec['rank_score'] = rank_score
            else:
                rec['rank_score'] = -1

        return sorted(recommendations, key=lambda x: x.get('rank_score', -1), reverse=True)
