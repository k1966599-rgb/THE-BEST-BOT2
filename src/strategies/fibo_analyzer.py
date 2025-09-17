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
    Implements Fibonacci analysis with divergence, confluence, and dynamic risk levels.
    """

    def __init__(self, config: Dict[str, Any], fetcher: DataFetcher):
        super().__init__(config)
        self.fetcher = fetcher
        p = config.get('strategy_params', {}).get('fibo_strategy', {})
        self.sma_fast = p.get('sma_period_fast', 50)
        self.sma_slow = p.get('sma_period_slow', 200)
        self.primary_lookback = p.get('primary_lookback', 120)
        self.secondary_lookback = p.get('secondary_lookback', 240)
        self.rsi_period = p.get('rsi_period', 14)
        self.stoch_window = p.get('stoch_window', 14)
        self.adx_window = p.get('adx_window', 14)
        self.atr_window = p.get('atr_window', 14)
        self.atr_multiplier = p.get('atr_multiplier', 2.0)

    def _find_confluence_zones(self, p_lvls: Dict, s_lvls: Dict, tol: float=0.005) -> List[Dict]:
        zones = []
        for pk, pv in p_lvls.items():
            for sk, sv in s_lvls.items():
                if abs(pv - sv) / pv <= tol:
                    zones.append({"level": (pv + sv) / 2, "p_level": pk, "s_level": sk})
        return zones

    def _calculate_confirmation_score(self, data: pd.DataFrame, trend: str, swings: Dict, zones: List) -> Dict[str, Any]:
        score, reasons = 0, []
        latest = data.iloc[-1]
        if trend == 'up' and detect_divergence(swings['lows'], data['rsi'], 'bullish'):
            score += 3; reasons.append("🔥 Bullish RSI Divergence")
        if zones: score += 2; reasons.append(f"Confluence Zone near ${zones[0]['level']:.2f}")
        if trend == 'up' and latest['rsi'] > 50: score += 1; reasons.append("RSI > 50")
        if trend == 'up' and latest['macd'] > latest['signal_line']: score += 1; reasons.append("MACD Bullish")
        pattern = get_candlestick_pattern(data.iloc[-3:])
        if trend == 'up' and pattern in ["Bullish Engulfing", "Hammer", "Morning Star"]:
            score += 2; reasons.append(f"Pattern: {pattern}")
        return {"score": score, "reasons": reasons, "pattern": pattern}

    def _calculate_risk_levels(self, trend: str, high: float, low: float, atr: float, extensions: Dict) -> Dict:
        if trend == 'up':
            stop_loss = low - (atr * self.atr_multiplier)
            targets = [v for k, v in extensions.items() if k in ['ext_1272', 'ext_1618', 'ext_2000']]
            entry = low + (atr * self.atr_multiplier) # Example entry
        else: # downtrend
            stop_loss = high + (atr * self.atr_multiplier)
            targets = [v for k, v in extensions.items() if k in ['ext_1272', 'ext_1618', 'ext_2000']]
            entry = high - (atr * self.atr_multiplier)
        return {"entry": entry, "stop_loss": stop_loss, "targets": targets}

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        if len(data) < self.secondary_lookback: return {'signal': 'HOLD', 'reason': 'Not enough data'}

        # --- 1. Indicators ---
        data['adx'] = calculate_adx(data, window=self.adx_window)
        data['atr'] = calculate_atr(data, window=self.atr_window)
        data['sma_fast'] = calculate_sma(data, self.sma_fast)
        data['sma_slow'] = calculate_sma(data, self.sma_slow)
        data['rsi'] = calculate_rsi(data, self.rsi_period)
        data = data.join(calculate_macd(data))
        data = data.join(calculate_stochastic(data, window=self.stoch_window))
        data.dropna(inplace=True)
        if len(data) < 50: return {'signal': 'HOLD', 'reason': 'Not enough data after calcs'}

        # --- 2. Trend & Swings ---
        latest = data.iloc[-1]
        if latest['adx'] < 20: return {'signal': 'HOLD', 'reason': f"Weak trend (ADX < 20)"}
        trend = 'up' if latest['sma_fast'] > latest['sma_slow'] else 'down'

        p_swings = find_swing_points(data, self.primary_lookback)
        s_swings = find_swing_points(data, self.secondary_lookback)
        if len(p_swings['highs'])<1 or len(p_swings['lows'])<1: return {'signal':'HOLD', 'reason':'Not enough primary swings'}

        p_high, p_low = p_swings['highs'][-1], p_swings['lows'][-1]
        s_high, s_low = s_swings['highs'][-1], s_swings['lows'][-1]

        # --- 3. Fibonacci & Confluence ---
        p_fibs = calculate_fib_levels(p_high['price'], p_low['price'], trend)
        s_fibs = calculate_fib_levels(s_high['price'], s_low['price'], trend)
        zones = self._find_confluence_zones(p_fibs, s_fibs)

        # --- 4. Score, Signal & Risk ---
        confirm = self._calculate_confirmation_score(data, trend, p_swings, zones)
        score = confirm['score']

        signal = "HOLD"
        risk_levels = {}
        extensions = {}
        if trend == 'up' and score >= 5:
            signal = "BUY"
            extensions = calculate_fib_extensions(p_high['price'], p_low['price'], trend)
            risk_levels = self._calculate_risk_levels(trend, p_high['price'], p_low['price'], latest['atr'], extensions)

        return {
            "trend": trend, "signal": signal, "reason": ", ".join(confirm['reasons']),
            "score": score, "swing_high": p_high, "swing_low": p_low,
            "retracements": p_fibs, "extensions": extensions,
            "confluence_zones": zones, "pattern": confirm['pattern'],
            "risk_levels": risk_levels, "latest_data": latest.to_dict(),
        }
