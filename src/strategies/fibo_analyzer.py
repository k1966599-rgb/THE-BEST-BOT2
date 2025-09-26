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


    def _initialize_result(self) -> Dict[str, Any]:
        """Initializes a default result dictionary."""
        return {
            "trend": "N/A", "signal": "HOLD", "reason": "", "score": 0,
            "swing_high": {}, "swing_low": {}, "retracements": {}, "extensions": {},
            "confluence_zones": [], "pattern": "N/A", "risk_levels": {},
            "scenarios": {}, "latest_data": {}, "current_price": 0
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

        # Initialize confirmations dictionary
        confirmations = {
            "confirmation_rsi": False,
            "confirmation_reversal_candle": False,
            "confirmation_break_618": False,
            "confirmation_volume": False, # Basic volume check, can be enhanced
        }

        bullish_reversal_patterns = ["Bullish Engulfing", "Hammer", "Morning Star", "Piercing Pattern", "Three White Soldiers"]
        bearish_reversal_patterns = ["Bearish Engulfing", "Shooting Star", "Evening Star", "Dark Cloud Cover", "Three Black Crows"]

        pattern = get_candlestick_pattern(data.iloc[-3:])

        if trend == 'up':
            if zones: score += 2; reasons.append(f"منطقة توافق قرب ${zones[0]['level']:.2f}")
            if latest['rsi'] > 50:
                score += 1; reasons.append("RSI > 50"); confirmations["confirmation_rsi"] = True
            if latest['macd'] > latest['signal_line']: score += 1; reasons.append("تقاطع MACD إيجابي")
            if pattern in bullish_reversal_patterns:
                score += 2; reasons.append(f"نموذج {pattern}"); confirmations["confirmation_reversal_candle"] = True

            # Check for break of 61.8% retracement level
            fib_618 = retracements.get('fib_618')
            if fib_618 and latest['close'] > fib_618:
                confirmations["confirmation_break_618"] = True

        else: # downtrend
            if zones: score += 2; reasons.append(f"منطقة توافق قرب ${zones[0]['level']:.2f}")
            if latest['rsi'] < 50:
                score += 1; reasons.append("RSI < 50"); confirmations["confirmation_rsi"] = True
            if latest['macd'] < latest['signal_line']: score += 1; reasons.append("تقاطع MACD سلبي")
            if pattern in bearish_reversal_patterns:
                score += 2; reasons.append(f"نموذج {pattern}"); confirmations["confirmation_reversal_candle"] = True

            # Check for break of 61.8% retracement level
            fib_618 = retracements.get('fib_618')
            if fib_618 and latest['close'] < fib_618:
                confirmations["confirmation_break_618"] = True

        # Basic volume check (e.g., volume is above its 20-period moving average)
        data['volume_sma'] = data['volume'].rolling(window=20).mean()
        if latest['volume'] > data['volume_sma'].iloc[-1]:
            confirmations["confirmation_volume"] = True

        return {"score": score, "reasons": reasons, "pattern": pattern, "confirmations": confirmations}

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

    def _find_recent_swing_points(self, data: pd.DataFrame, prominence: int = 1) -> (Dict, Dict):
        """
        Finds the most recent significant swing high and low using scipy's
        find_peaks for better accuracy.
        """
        recent_data = data.tail(100).copy()

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

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        result = self._initialize_result()
        # A data length check will be performed after indicator calculation

        # --- 1. Calculate all indicators and clean data FIRST ---
        data['adx'] = calculate_adx(data, window=self.adx_window)
        data['atr'] = calculate_atr(data, window=self.atr_window)
        data['sma_fast'] = calculate_sma(data, window=self.sma_fast_period)
        data['sma_slow'] = calculate_sma(data, window=self.sma_slow_period)
        data['rsi'] = calculate_rsi(data, window=self.rsi_period)
        data = data.join(calculate_macd(data))
        data = data.join(calculate_stochastic(data, window=self.stoch_window))

        # Drop rows with NaN values resulting from indicator calculations
        data.dropna(inplace=True)

        # After cleaning, reset the index to ensure .iloc works correctly
        data.reset_index(drop=True, inplace=True)

        if len(data) < 50:
            result['reason'] = 'Not enough data after indicator calculations'; return result

        latest = data.iloc[-1]
        result.update({"latest_data": latest.to_dict(), "current_price": latest['close']})

        # --- 2. Trend & Swings (on clean data) ---
        # Determine the main trend from the moving averages for context
        main_trend = 'up' if latest['sma_fast'] > latest['sma_slow'] else 'down'
        result['trend'] = main_trend

        # Find the most recent significant swing points for Fibonacci analysis.
        p_high, p_low = self._find_recent_swing_points(data, prominence=1)

        # If swings are not found, fallback gracefully
        if p_high is None or p_low is None:
            result['reason'] = 'Could not determine recent swing points for analysis.'
            return result

        # The trend for Fibo drawing is determined by which came last
        trend = 'up' if p_high['index'] > p_low['index'] else 'down'

        # The score and confirmation section is no longer relevant with this simple approach.
        # We will bypass it and go straight to scenario generation.
        p_swings = {'highs': [p_high], 'lows': [p_low]} # Create a dummy swings object for compatibility
        s_swings = p_swings

        # Ensure p_high is actually higher than p_low
        # Update the result with the found swings first for consistent output
        result.update({"swing_high": p_high, "swing_low": p_low})

        if p_high['price'] <= p_low['price']:
            result['reason'] = f"Invalid Fibo points (H:{p_high['price']} <= L:{p_low['price']})"; return result

        s_high, s_low = s_swings['highs'][-1] if s_swings['highs'] else p_high, s_swings['lows'][-1] if s_swings['lows'] else p_low

        # --- 3. Fibonacci & Confluence ---
        result['retracements'] = calculate_fib_levels(p_high['price'], p_low['price'], trend)
        result['extensions'] = calculate_fib_extensions(p_high['price'], p_low['price'], trend)
        result['confluence_zones'] = self._find_confluence_zones(result['retracements'], calculate_fib_levels(s_high['price'], s_low['price'], trend))

        # --- 4. Score, Signal & Scenarios ---
        confirm_data = self._calculate_confirmation_score(data, trend, p_swings, result['confluence_zones'], result['retracements'])
        result.update(confirm_data)

        if trend == 'up' and result['score'] >= 5: result['signal'] = "BUY"
        elif trend == 'down' and result['score'] >= 5: result['signal'] = "SELL"

        result['scenarios'] = self._generate_scenarios(result)

        return result
