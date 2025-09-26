import pandas as pd
import logging
from typing import Dict, Any, List
from scipy.signal import find_peaks
from src.data_retrieval.data_fetcher import DataFetcher

from .base_strategy import BaseStrategy
from ..utils.indicators import (
    calculate_sma, calculate_fib_levels,
    calculate_fib_extensions, calculate_rsi, calculate_macd,
    calculate_stochastic, calculate_bollinger_bands, calculate_adx,
    calculate_atr
)
from ..utils.patterns import get_candlestick_pattern

class FiboAnalyzer(BaseStrategy):
    """
    Implements the user's detailed Fibonacci methodology with a comprehensive
    confirmation scoring system, dynamic risk levels, and intelligent scenarios.
    """

    def __init__(self, config: Dict[str, Any], fetcher: DataFetcher):
        super().__init__(config)
        self.fetcher = fetcher
        p = config.get('strategy_params', {}).get('fibo_strategy', {})
        self.sma_fast_period = p.get('sma_period_fast', 50)
        self.sma_slow_period = p.get('sma_period_slow', 200)
        self.rsi_period = p.get('rsi_period', 14)
        self.stoch_window = p.get('stoch_window', 14)
        self.adx_window = p.get('adx_window', 14)
        self.atr_window = p.get('atr_window', 14)
        self.atr_multiplier = p.get('atr_multiplier', 2.0)
        self.fib_lookback = p.get('fib_lookback', 50)
        self.volume_period = p.get('volume_period', 20)
        self.volume_multiplier = p.get('volume_multiplier', 1.5)
        self.weights = p.get('scoring_weights', {
            'confluence_zone': 2, 'rsi_confirm': 1, 'macd_confirm': 1,
            'reversal_pattern': 2, 'volume_confirm': 1
        })
        self.adx_threshold = p.get('adx_trend_threshold', 25)
        self.swing_atr_multiplier = p.get('swing_prominence_atr_multiplier', 0.5)


    def _initialize_result(self) -> Dict[str, Any]:
        """Initializes a default result dictionary."""
        return {
            "trend": "N/A", "signal": "HOLD", "reason": "", "score": 0,
            "swing_high": {}, "swing_low": {}, "retracements": {}, "extensions": {},
            "confluence_zones": [], "pattern": "N/A", "risk_levels": {},
            "scenarios": {}, "latest_data": {}, "current_price": 0,
            "confidence": 0, "rr_ratio": 0.0
        }

    def _find_confluence_zones(self, p_lvls: Dict, s_lvls: Dict, tol: float=0.005) -> List[Dict]:
        zones = []
        for pk, pv in p_lvls.items():
            for sk, sv in s_lvls.items():
                if abs(pv - sv) / pv <= tol:
                    zones.append({"level": (pv + sv) / 2, "p_level": pk, "s_level": sk})
        return zones

    def _calculate_confirmation_score(self, data: pd.DataFrame, trend: str, swings: Dict, zones: List, retracements: Dict) -> Dict[str, Any]:
        score, reasons = 0, []
        latest = data.iloc[-1]
        data['volume_sma'] = data['volume'].rolling(window=self.volume_period).mean()

        confirmations = {
            "confirmation_rsi": False, "confirmation_reversal_candle": False,
            "confirmation_break_618": False, "confirmation_volume": False,
        }

        bullish_patterns = ["Bullish Engulfing", "Hammer", "Morning Star", "Piercing Pattern", "Three White Soldiers", "Tweezer Bottom"]
        bearish_patterns = ["Bearish Engulfing", "Shooting Star", "Evening Star", "Dark Cloud Cover", "Three Black Crows", "Tweezer Top"]

        pattern = get_candlestick_pattern(data.tail(3))
        is_reversal_pattern = pattern in bullish_patterns or pattern in bearish_patterns

        # --- Scoring Logic ---
        if trend == 'up':
            if zones:
                score += self.weights.get('confluence_zone', 2); reasons.append(f"منطقة توافق قرب ${zones[0]['level']:.2f}")
            if latest['rsi'] > 50:
                score += self.weights.get('rsi_confirm', 1); reasons.append("RSI > 50"); confirmations["confirmation_rsi"] = True
            if latest['macd'] > latest['signal_line']:
                score += self.weights.get('macd_confirm', 1); reasons.append("تقاطع MACD إيجابي")
            if pattern in bullish_patterns:
                score += self.weights.get('reversal_pattern', 2); reasons.append(f"نموذج {pattern}"); confirmations["confirmation_reversal_candle"] = True
            fib_618 = retracements.get('fib_618')
            if fib_618 and latest['close'] > fib_618: confirmations["confirmation_break_618"] = True
        else:  # downtrend
            if zones:
                score += self.weights.get('confluence_zone', 2); reasons.append(f"منطقة توافق قرب ${zones[0]['level']:.2f}")
            if latest['rsi'] < 50:
                score += self.weights.get('rsi_confirm', 1); reasons.append("RSI < 50"); confirmations["confirmation_rsi"] = True
            if latest['macd'] < latest['signal_line']:
                score += self.weights.get('macd_confirm', 1); reasons.append("تقاطع MACD سلبي")
            if pattern in bearish_patterns:
                score += self.weights.get('reversal_pattern', 2); reasons.append(f"نموذج {pattern}"); confirmations["confirmation_reversal_candle"] = True
            fib_618 = retracements.get('fib_618')
            if fib_618 and latest['close'] < fib_618: confirmations["confirmation_break_618"] = True

        # Enhanced Volume Confirmation: Check for high volume only on reversal patterns
        if is_reversal_pattern:
            volume_threshold = data['volume_sma'].iloc[-2] * self.volume_multiplier # Use previous candle's SMA
            if latest['volume'] > volume_threshold:
                score += self.weights.get('volume_confirm', 1)
                reasons.append("تأكيد حجم التداول")
                confirmations["confirmation_volume"] = True

        return {"score": score, "reasons": reasons, "pattern": pattern, "confirmations": confirmations}

    def _calculate_risk_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates confidence level and risk/reward ratio."""
        score = result.get('score', 0)
        max_score = sum(self.weights.values())

        # Calculate confidence level (e.g., from a base of 50% to a max of 95%)
        confidence = 50 + (score / max_score) * 45 if max_score > 0 else 50
        result['confidence'] = round(confidence)

        # Calculate Risk/Reward Ratio from the primary scenario
        scenario1 = result.get('scenarios', {}).get('scenario1', {})
        entry_price = scenario1.get('entry')
        stop_loss = scenario1.get('stop_loss')
        target = scenario1.get('target')

        if entry_price and stop_loss and target:
            potential_loss = abs(entry_price - stop_loss)
            potential_profit = abs(target - entry_price)

            if potential_loss > 0:
                rr_ratio = potential_profit / potential_loss
                result['rr_ratio'] = round(rr_ratio, 2)
            else:
                result['rr_ratio'] = float('inf')

        return result

    def _generate_scenarios(self, result: Dict) -> Dict:
        trend = result['trend']
        score = result['score']
        high, low = result['swing_high']['price'], result['swing_low']['price']
        entry = result['current_price']
        extensions = result['extensions']

        prob_primary = min(60 + (score * 5), 90)
        prob_secondary = 100 - prob_primary

        if trend == 'up':
            primary = {"title": "صعود نحو الأهداف", "prob": prob_primary, "target": extensions.get('ext_1618', high*1.05), "entry": entry, "stop_loss": low - (result['latest_data']['atr'] * self.atr_multiplier)}
            secondary = {"title": "فشل السيناريو والهبوط", "prob": prob_secondary, "target": low, "entry": entry, "stop_loss": high}
        else: #downtrend
            primary = {"title": "هبوط نحو الأهداف", "prob": prob_primary, "target": extensions.get('ext_1618', low*0.95), "entry": entry, "stop_loss": high + (result['latest_data']['atr'] * self.atr_multiplier)}
            secondary = {"title": "فشل السيناريو والصعود", "prob": prob_secondary, "target": high, "entry": entry, "stop_loss": low}

        return {"scenario1": primary, "scenario2": secondary}

    def _find_recent_swing_points(self, data: pd.DataFrame, avg_atr: float) -> (Dict, Dict):
        """
        Finds the most recent significant swing high and low.
        The prominence is calculated dynamically based on the average ATR to adapt
        to different market volatility conditions.
        """
        recent_data = data.tail(100).copy()

        # Dynamic prominence based on volatility (ATR)
        prominence = avg_atr * self.swing_atr_multiplier

        # Find swing highs (peaks)
        high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=prominence)

        # Find swing lows (valleys) by finding peaks in the inverted 'low' series
        low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=prominence)

        if high_peaks_indices.size == 0 or low_peaks_indices.size == 0:
            # Fallback to absolute min/max of the recent data if no peaks are found
            high_idx = recent_data['high'].idxmax()
            low_idx = recent_data['low'].idxmin()
            p_high = {'price': recent_data.loc[high_idx, 'high'], 'index': high_idx}
            p_low = {'price': recent_data.loc[low_idx, 'low'], 'index': low_idx}
            return p_high, p_low

        # Get the most recent high and low from the detected peaks
        latest_high_idx = high_peaks_indices[-1]
        latest_low_idx = low_peaks_indices[-1]

        # Ensure we are using the original DataFrame's index
        original_high_idx = recent_data.index[latest_high_idx]
        original_low_idx = recent_data.index[latest_low_idx]

        p_high = {'price': recent_data.loc[original_high_idx, 'high'], 'index': original_high_idx}
        p_low = {'price': recent_data.loc[original_low_idx, 'low'], 'index': original_low_idx}

        return p_high, p_low

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculates all technical indicators and cleans the data."""
        data['adx'] = calculate_adx(data, window=self.adx_window)
        data['atr'] = calculate_atr(data, window=self.atr_window)
        data['sma_fast'] = calculate_sma(data, window=self.sma_fast_period)
        data['sma_slow'] = calculate_sma(data, window=self.sma_slow_period)
        data['rsi'] = calculate_rsi(data, window=self.rsi_period)
        data = data.join(calculate_macd(data))
        data = data.join(calculate_stochastic(data, window=self.stoch_window))
        data.dropna(inplace=True)
        data.reset_index(drop=True, inplace=True)
        return data

    def _analyze_trend_and_swings(self, data: pd.DataFrame, result: Dict) -> bool:
        """Determines trend, finds swing points, and updates the result dict."""
        latest = data.iloc[-1]
        if latest['adx'] < self.adx_threshold:
            result['trend'] = 'Sideways'
        else:
            result['trend'] = 'up' if latest['sma_fast'] > latest['sma_slow'] else 'down'

        avg_atr = data['atr'].mean()
        p_high, p_low = self._find_recent_swing_points(data, avg_atr=avg_atr)

        if p_high is None or p_low is None:
            result['reason'] = 'Could not determine recent swing points.'
            return False

        result.update({"swing_high": p_high, "swing_low": p_low})

        if p_high['price'] <= p_low['price']:
            result['reason'] = f"Invalid Fibo points (H:{p_high['price']} <= L:{p_low['price']})"
            return False

        return True

    def _analyze_fibonacci_and_score(self, data: pd.DataFrame, result: Dict):
        """Calculates Fibonacci levels, confluence zones, and the confirmation score."""
        p_high = result['swing_high']
        p_low = result['swing_low']
        fibo_trend = 'up' if p_high['index'] > p_low['index'] else 'down'

        # In this version, primary and secondary swings are the same.
        s_high, s_low = p_high, p_low

        result['retracements'] = calculate_fib_levels(p_high['price'], p_low['price'], fibo_trend)
        result['extensions'] = calculate_fib_extensions(p_high['price'], p_low['price'], fibo_trend)
        result['confluence_zones'] = self._find_confluence_zones(result['retracements'], calculate_fib_levels(s_high['price'], s_low['price'], fibo_trend))

        p_swings = {'highs': [p_high], 'lows': [p_low]}
        confirm_data = self._calculate_confirmation_score(data, fibo_trend, p_swings, result['confluence_zones'], result['retracements'])
        result.update(confirm_data)

        if fibo_trend == 'up' and result['score'] >= 5:
            result['signal'] = "BUY"
        elif fibo_trend == 'down' and result['score'] >= 5:
            result['signal'] = "SELL"

    def _finalize_analysis(self, result: Dict):
        """Generates scenarios and calculates final risk metrics."""
        result['scenarios'] = self._generate_scenarios(result)
        self._calculate_risk_metrics(result) # This function modifies result in-place

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        result = self._initialize_result()

        data = self._prepare_data(data)
        if len(data) < 50:
            result['reason'] = 'Not enough data after indicator calculations'
            return result

        result.update({"latest_data": data.iloc[-1].to_dict(), "current_price": data.iloc[-1]['close']})

        if not self._analyze_trend_and_swings(data, result):
            return result

        self._analyze_fibonacci_and_score(data, result)
        self._finalize_analysis(result)

        return result
