import pandas as pd
import logging
from typing import Dict, Any, List
from scipy.signal import find_peaks
from src.data_retrieval.data_fetcher import DataFetcher

from .base_strategy import BaseStrategy
from .exceptions import InsufficientDataError
from ..utils.indicators import (
    calculate_sma, calculate_fib_levels,
    calculate_fib_extensions, calculate_rsi, calculate_macd,
    calculate_stochastic, calculate_bollinger_bands, calculate_adx,
    calculate_atr
)
from ..utils.patterns import get_candlestick_pattern

class FiboAnalyzer(BaseStrategy):
    """
    Implements a detailed Fibonacci methodology with a comprehensive
    confirmation scoring system, dynamic risk levels, and intelligent scenarios.
    """

    def __init__(self, config: Dict[str, Any], fetcher: DataFetcher, timeframe: str = None):
        super().__init__(config)
        self.fetcher = fetcher

        base_params = config.get('strategy_params', {}).get('fibo_strategy', {})
        timeframe_overrides = base_params.get('timeframe_overrides', {})
        specific_params = timeframe_overrides.get(timeframe, {})
        p = {**base_params, **specific_params}

        self.sma_fast_period = p.get('sma_period_fast', 50)
        self.sma_slow_period = p.get('sma_period_slow', 200)
        self.rsi_period = p.get('rsi_period', 14)
        self.stoch_window = p.get('stoch_window', 14)
        self.adx_window = p.get('adx_window', 14)
        self.atr_window = p.get('atr_window', 14)
        self.fib_lookback = p.get('fib_lookback', 50)
        self.swing_lookback_period = p.get('swing_lookback_period', 100)
        self.volume_period = p.get('volume_period', 20)

        risk_config = config.get('risk_management', {})
        self.atr_multiplier = risk_config.get('atr_multiplier_sl', 2.0)

        self.swing_atr_multiplier = p.get('swing_prominence_atr_multiplier', 0.5)
        self.volume_spike_multiplier = p.get('volume_spike_multiplier', 2.0)
        self.adx_threshold = p.get('adx_trend_threshold', 25)
        self.signal_threshold = p.get('signal_threshold', 5)
        self.require_adx_confirmation = p.get('require_adx_confirmation', True)

        self.weights = p.get('scoring_weights', {
            'confluence_zone': 2, 'rsi_confirm': 1, 'macd_confirm': 1,
            'stoch_confirm': 1, 'reversal_pattern': 2, 'volume_spike': 2
        })

    def _initialize_result(self) -> Dict[str, Any]:
        """Initializes a default result dictionary."""
        return {
            "trend": "N/A", "signal": "HOLD", "reason": "", "final_reason": "", "score": 0,
            "swing_high": {}, "swing_low": {}, "retracements": {}, "extensions": {},
            "confluence_zones": [], "pattern": "N/A", "risk_levels": {},
            "scenarios": {}, "latest_data": {}, "current_price": 0,
            "confidence": 0, "rr_ratio": 0.0, "weights": {},
            "higher_tf_trend_info": None, "mta_override": False
        }

    def _find_confluence_zones(self, p_lvls: Dict, s_lvls: Dict, tol: float=0.005) -> List[Dict]:
        zones = []
        for pk, pv in p_lvls.items():
            for sk, sv in s_lvls.items():
                if abs(pv - sv) / pv <= tol:
                    zones.append({"level": (pv + sv) / 2, "p_level": pk, "s_level": sk})
        return zones

    def _calculate_confirmation_score(self, data: pd.DataFrame, fibo_trend: str) -> Dict[str, Any]:
        score, reasons = 0, []
        data['volume_sma'] = data['volume'].rolling(window=self.volume_period).mean()
        latest = data.iloc[-1]

        bullish_patterns = ["Bullish Engulfing", "Hammer", "Morning Star", "Piercing Pattern", "Three White Soldiers", "Tweezer Bottom"]
        bearish_patterns = ["Bearish Engulfing", "Shooting Star", "Evening Star", "Dark Cloud Cover", "Three Black Crows", "Tweezer Top"]
        pattern = get_candlestick_pattern(data.tail(3))

        if fibo_trend == 'up':
            if latest['rsi'] > 50:
                score += self.weights.get('rsi_confirm', 1); reasons.append(f"مؤشر القوة النسبية فوق 50 (القيمة: {latest['rsi']:.2f})")
            if latest['macd'] > latest['signal_line']:
                score += self.weights.get('macd_confirm', 1); reasons.append("تقاطع MACD إيجابي")
            if latest['stoch_k'] < 30 and latest['stoch_k'] > latest['stoch_d']:
                score += self.weights.get('stoch_confirm', 1); reasons.append(f"مؤشر ستوكاستيك يظهر انعكاسًا من التشبع البيعي")
            if pattern in bullish_patterns:
                score += self.weights.get('reversal_pattern', 2); reasons.append(f"نموذج انعكاسي صاعد: {pattern}")
        else:
            if latest['rsi'] < 50:
                score += self.weights.get('rsi_confirm', 1); reasons.append(f"مؤشر القوة النسبية تحت 50 (القيمة: {latest['rsi']:.2f})")
            if latest['macd'] < latest['signal_line']:
                score += self.weights.get('macd_confirm', 1); reasons.append("تقاطع MACD سلبي")
            if latest['stoch_k'] > 70 and latest['stoch_k'] < latest['stoch_d']:
                score += self.weights.get('stoch_confirm', 1); reasons.append(f"مؤشر ستوكاستيك يظهر انعكاسًا من التشبع الشرائي")
            if pattern in bearish_patterns:
                score += self.weights.get('reversal_pattern', 2); reasons.append(f"نموذج انعكاسي هابط: {pattern}")

        volume_threshold = latest['volume_sma'] * self.volume_spike_multiplier
        if latest['volume'] > volume_threshold:
            if fibo_trend == 'up' and latest['close'] > latest['open']:
                score += self.weights.get('volume_spike', 2); reasons.append("✅ تأكيد طفرة حجم تداول صاعدة")
            elif fibo_trend == 'down' and latest['close'] < latest['open']:
                score += self.weights.get('volume_spike', 2); reasons.append("✅ تأكيد طفرة حجم تداول هابطة")

        return {"score": score, "reasons": reasons, "pattern": pattern}

    def _calculate_risk_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        score = result.get('score', 0)
        max_score = sum(self.weights.values())
        result['confidence'] = round(50 + (score / max_score) * 45 if max_score > 0 else 50)
        scenario1 = result.get('scenarios', {}).get('scenario1', {})
        entry_price = scenario1.get('entry')
        stop_loss = scenario1.get('stop_loss')
        target = scenario1.get('target')

        if entry_price and stop_loss and target:
            potential_loss = abs(entry_price - stop_loss)
            potential_profit = abs(target - entry_price)

            # Avoid division by zero if entry and stop-loss are the same
            if potential_loss > 0:
                result['rr_ratio'] = round(potential_profit / potential_loss, 2)
            else:
                # If there's no risk, the ratio is effectively infinite, but we'll represent it as 0 for practicality.
                result['rr_ratio'] = 0.0
        return result

    def _generate_scenarios(self, result: Dict) -> Dict:
        fibo_trend = result.get('fibo_trend', 'up')
        signal = result.get('signal', 'HOLD')
        score = result.get('score', 0)
        high, low = result['swing_high']['price'], result['swing_low']['price']
        entry = result['current_price']
        extensions = result['extensions']
        atr = result.get('latest_data', {}).get('atr', 0)

        prob_primary = min(60 + (score * 4), 95) if signal in ['BUY', 'SELL'] else 50
        prob_secondary = 100 - prob_primary

        if fibo_trend == 'up':
            primary = {"title": "صعود نحو الأهداف", "prob": prob_primary, "target": extensions.get('ext_1618', high * 1.05), "entry": entry, "stop_loss": low - (atr * self.atr_multiplier)}
            secondary = {"title": "فشل السيناريو والهبوط", "prob": prob_secondary, "target": low, "entry": entry, "stop_loss": high + (atr * self.atr_multiplier)}
        else:
            diff = high - low
            primary = {"title": "هبوط نحو الأهداف", "prob": prob_primary, "target": low - (diff * 1.618), "entry": entry, "stop_loss": high + (atr * self.atr_multiplier)}
            secondary = {"title": "فشل السيناريو والصعود", "prob": prob_secondary, "target": high, "entry": entry, "stop_loss": low - (atr * self.atr_multiplier)}

        if signal == 'HOLD':
            primary['title'] = f"السيناريو المحتمل ({primary['title']})"
            secondary['title'] = f"السيناريو البديل ({secondary['title']})"

        return {"scenario1": primary, "scenario2": secondary}

    def _find_recent_swing_points(self, data: pd.DataFrame, avg_atr: float) -> (Dict, Dict):
        recent_data = data.tail(self.swing_lookback_period).copy()
        prominence = avg_atr * self.swing_atr_multiplier
        high_peaks_indices, _ = find_peaks(recent_data['high'], prominence=prominence)
        low_peaks_indices, _ = find_peaks(-recent_data['low'], prominence=prominence)

        # Fallback to absolute max/min if no significant peaks are found
        if high_peaks_indices.size == 0 or low_peaks_indices.size == 0:
            high_idx, low_idx = recent_data['high'].idxmax(), recent_data['low'].idxmin()
            if recent_data.loc[high_idx, 'high'] <= recent_data.loc[low_idx, 'low']:
                return None, None
            return {'price': recent_data.loc[high_idx, 'high'], 'index': high_idx}, {'price': recent_data.loc[low_idx, 'low'], 'index': low_idx}

        high_peak_indices_orig = recent_data.index[high_peaks_indices]
        low_peak_indices_orig = recent_data.index[low_peaks_indices]

        latest_high_peak_idx = high_peak_indices_orig[-1]
        latest_low_peak_idx = low_peak_indices_orig[-1]

        # Determine the most recent swing by finding the last peak (high or low)
        # and then finding the preceding opposite peak.
        if latest_high_peak_idx > latest_low_peak_idx:
            # Last significant move was up. The swing is from a low to a high.
            final_swing_high_idx = latest_high_peak_idx
            prior_low_peaks = low_peak_indices_orig[low_peak_indices_orig < final_swing_high_idx]
            if prior_low_peaks.size == 0:
                return None, None
            final_swing_low_idx = prior_low_peaks[-1]
        else:
            # Last significant move was down. The swing is from a high to a low.
            final_swing_low_idx = latest_low_peak_idx
            prior_high_peaks = high_peak_indices_orig[high_peak_indices_orig < final_swing_low_idx]
            if prior_high_peaks.size == 0:
                return None, None
            final_swing_high_idx = prior_high_peaks[-1]

        swing_high = {'price': recent_data.loc[final_swing_high_idx, 'high'], 'index': final_swing_high_idx}
        swing_low = {'price': recent_data.loc[final_swing_low_idx, 'low'], 'index': final_swing_low_idx}

        # Final sanity check
        if swing_high['price'] <= swing_low['price']:
            return None, None

        return swing_high, swing_low

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data['adx'] = calculate_adx(data, window=self.adx_window)
        data['atr'] = calculate_atr(data, window=self.atr_window)
        data['sma_fast'] = calculate_sma(data, window=self.sma_fast_period)
        data['sma_slow'] = calculate_sma(data, window=self.sma_slow_period)
        data['rsi'] = calculate_rsi(data, window=self.rsi_period)
        data = data.join(calculate_macd(data))
        data = data.join(calculate_stochastic(data, window=self.stoch_window))
        return data

    def _analyze_trend_and_swings(self, data: pd.DataFrame, result: Dict) -> bool:
        latest = data.iloc[-1]
        result['trend'] = 'up' if latest['sma_fast'] > latest['sma_slow'] else 'down'
        if latest['adx'] < self.adx_threshold: result['trend'] = 'Sideways'
        p_high, p_low = self._find_recent_swing_points(data, data['atr'].mean())
        if p_high is None or p_low is None or p_high['price'] <= p_low['price']:
            result['reason'] = "لم يتم تحديد نقاط انعكاس صالحة."
            return False
        result.update({"swing_high": p_high, "swing_low": p_low})
        return True

    def _analyze_fibonacci_and_score(self, data: pd.DataFrame, result: Dict):
        p_high, p_low = result['swing_high'], result['swing_low']
        fibo_trend = 'up' if p_high['index'] > p_low['index'] else 'down'
        result['fibo_trend'] = fibo_trend
        result['retracements'] = calculate_fib_levels(p_high['price'], p_low['price'], fibo_trend)
        result['extensions'] = calculate_fib_extensions(p_high['price'], p_low['price'], fibo_trend)
        result['confluence_zones'] = self._find_confluence_zones(result['retracements'], result['extensions'])

        confirm_data = self._calculate_confirmation_score(data, fibo_trend)
        result.update(confirm_data)

        score_met = result['score'] >= self.signal_threshold
        adx_value = result.get('latest_data', {}).get('adx', 0)
        adx_confirmed = not self.require_adx_confirmation or (adx_value >= self.adx_threshold)

        if score_met and adx_confirmed:
            result['signal'] = "BUY" if fibo_trend == 'up' else "SELL"
            result['final_reason'] = f"بناءً على {result['score']} نقطة قوة مع اتجاه {fibo_trend} مؤكد."
        elif score_met and not adx_confirmed:
            result['final_reason'] = f"تم تحقيق النقاط المطلوبة لكن قوة الاتجاه ضعيفة (ADX: {adx_value:.2f})"
        else:
            result['final_reason'] = f"لعدم تحقيق الحد الأدنى من نقاط القوة ({result['score']}/{self.signal_threshold})"

        # --- MTA Confirmation ---
        higher_tf_trend_info = result.get('higher_tf_trend_info')
        if higher_tf_trend_info and result['signal'] != 'HOLD':
            higher_trend = higher_tf_trend_info.get('trend')
            higher_tf = higher_tf_trend_info.get('timeframe')

            override = False
            reason = ""
            # Override BUY signal if higher trend is down
            if higher_trend == 'down' and result['signal'] == 'BUY':
                override = True
                reason = "هابط"
            # Override SELL signal if higher trend is up
            elif higher_trend == 'up' and result['signal'] == 'SELL':
                override = True
                reason = "صاعد"

            if override:
                original_signal = result['signal']
                result['signal'] = 'HOLD'
                result['final_reason'] = f"تم إلغاء إشارة {original_signal} لأن الاتجاه على الإطار الأعلى ({higher_tf}) {reason}."
                result['mta_override'] = True

    def _finalize_analysis(self, result: Dict):
        result['scenarios'] = self._generate_scenarios(result)
        self._calculate_risk_metrics(result)
        self._identify_key_levels(result)

    def _identify_key_levels(self, result: Dict):
        """Identifies and adds key support and resistance levels to the result."""
        levels = []
        swing_high = result.get('swing_high', {}).get('price')
        swing_low = result.get('swing_low', {}).get('price')
        retracements = result.get('retracements', {})

        if swing_high: levels.append({'level': swing_high, 'type': 'Swing High'})
        if swing_low: levels.append({'level': swing_low, 'type': 'Swing Low'})

        fib_levels_to_add = ['fib_382', 'fib_500', 'fib_618']
        for key in fib_levels_to_add:
            if key in retracements:
                level_ratio = int(key.split('_')[1]) / 1000
                levels.append({'level': retracements[key], 'type': f"Fibo {level_ratio}"})

        # Sort levels by price
        levels.sort(key=lambda x: x['level'], reverse=True)
        result['key_levels'] = levels

    def get_analysis(self, data: pd.DataFrame, symbol: str, timeframe: str, higher_tf_trend_info: Dict[str, Any] = None) -> Dict[str, Any]:
        data = self._prepare_data(data)
        data.dropna(subset=['sma_slow'], inplace=True)
        data.reset_index(drop=True, inplace=True)

        if len(data) < self.swing_lookback_period:
            raise InsufficientDataError(f'Not enough data for swing analysis.', required=self.swing_lookback_period, available=len(data))

        result = self._initialize_result()
        result.update({
            "latest_data": data.iloc[-1].to_dict(),
            "current_price": data.iloc[-1]['close'],
            "higher_tf_trend_info": higher_tf_trend_info
        })

        if not self._analyze_trend_and_swings(data, result):
            return result

        self._analyze_fibonacci_and_score(data, result)
        self._finalize_analysis(result)
        result['weights'] = self.weights
        return result