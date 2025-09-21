import pandas as pd
from typing import Dict, Any, List
from src.data_retrieval.data_fetcher import DataFetcher

from .base_strategy import BaseStrategy
from ..utils.indicators import (
    calculate_sma, find_swing_points, calculate_fib_levels,
    calculate_fib_extensions, calculate_rsi, calculate_macd,
    calculate_stochastic, calculate_bollinger_bands, calculate_adx,
    detect_divergence, calculate_atr
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
        self.primary_lookback = p.get('primary_lookback', 120)
        self.secondary_lookback = p.get('secondary_lookback', 240)
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
            if detect_divergence(swings['lows'], data['rsi'], 'bullish'): score += 3; reasons.append("🔥 انحراف إيجابي (RSI)")
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
            if detect_divergence(swings['highs'], data['rsi'], 'bearish'): score += 3; reasons.append("🔥 انحراف سلبي (RSI)")
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

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        result = self._initialize_result()
        if len(data) < self.secondary_lookback:
            result['reason'] = 'Not enough data'; return result

        # --- 1. Indicators ---
        data['adx'] = calculate_adx(data, window=self.adx_window)
        data['atr'] = calculate_atr(data, window=self.atr_window)
        data['sma_fast'] = calculate_sma(data, window=self.sma_fast_period)
        data['sma_slow'] = calculate_sma(data, window=self.sma_slow_period)
        data['rsi'] = calculate_rsi(data, window=self.rsi_period)
        data = data.join(calculate_macd(data))
        data = data.join(calculate_stochastic(data, window=self.stoch_window))
        data.dropna(inplace=True)
        if len(data) < 50:
            result['reason'] = 'Not enough data after calcs'; return result

        latest = data.iloc[-1]
        result.update({"latest_data": latest.to_dict(), "current_price": latest['close']})

        # --- 2. Trend & Swings ---
        if latest['adx'] < 20:
            result['reason'] = f"Weak trend (ADX: {latest['adx']:.1f})"; return result

        trend = 'up' if latest['sma_fast'] > latest['sma_slow'] else 'down'
        result['trend'] = trend

        p_swings = find_swing_points(data, self.primary_lookback)
        s_swings = find_swing_points(data, self.secondary_lookback)
        if len(p_swings['highs'])<1 or len(p_swings['lows'])<1:
            result['reason'] = 'Not enough primary swings'; return result

        p_high, p_low = p_swings['highs'][-1], p_swings['lows'][-1]
        s_high, s_low = s_swings['highs'][-1] if s_swings['highs'] else p_high, s_swings['lows'][-1] if s_swings['lows'] else p_low
        result.update({"swing_high": p_high, "swing_low": p_low})

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
