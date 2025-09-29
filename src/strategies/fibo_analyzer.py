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
        self.swing_comparison_window = p.get('swing_comparison_window', 5)
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
        # Use the 'best' entry price from the entry zone for R/R calculation
        entry_price = scenario1.get('entry_zone', {}).get('best')
        stop_loss = scenario1.get('stop_loss')
        # Use the first take-profit target for a conservative R/R calculation
        target = scenario1.get('targets', {}).get('tp1')

        if entry_price and stop_loss and target:
            potential_loss = abs(entry_price - stop_loss)
            potential_profit = abs(target - entry_price)

            # Avoid division by zero if entry and stop-loss are the same
            if potential_loss > 0:
                result['rr_ratio'] = round(potential_profit / potential_loss, 2)
            else:
                result['rr_ratio'] = 0.0
        else:
             result['rr_ratio'] = 0.0 # Default if values are missing

        return result

    def _generate_scenarios(self, result: Dict) -> Dict:
        fibo_trend = result.get('fibo_trend', 'up')
        signal = result.get('signal', 'HOLD')
        score = result.get('score', 0)
        high, low = result['swing_high']['price'], result['swing_low']['price']
        retracements = result.get('retracements', {})
        extensions = result.get('extensions', {})
        atr = result.get('latest_data', {}).get('atr', 0)

        # Define Entry Zone based on Fibonacci retracement levels
        entry_zone = {
            "best": retracements.get('fib_618'),
            "start": retracements.get('fib_500'),
            "end": retracements.get('fib_618')
        }
        if entry_zone['start'] and entry_zone['end']:
            if (fibo_trend == 'up' and entry_zone['start'] < entry_zone['end']) or \
               (fibo_trend == 'down' and entry_zone['start'] > entry_zone['end']):
                entry_zone['start'], entry_zone['end'] = entry_zone['end'], entry_zone['start']

        # Define Multiple Take-Profit Targets
        targets = {
            "tp1": extensions.get('ext_1272'),
            "tp2": extensions.get('ext_1618'),
            "tp3": extensions.get('ext_2618')
        }

        prob_primary = min(60 + (score * 4), 95) if signal in ['BUY', 'SELL'] else 50
        prob_secondary = 100 - prob_primary

        if fibo_trend == 'up':
            primary = {
                "title": "صعود نحو الأهداف", "prob": prob_primary,
                "entry_zone": entry_zone,
                "stop_loss": low - (atr * self.atr_multiplier),
                "targets": targets
            }
            secondary = {"title": "فشل السيناريو والهبوط", "prob": prob_secondary, "target": low, "stop_loss": high + (atr * self.atr_multiplier)}
        else:
            primary = {
                "title": "هبوط نحو الأهداف", "prob": prob_primary,
                "entry_zone": entry_zone,
                "stop_loss": high + (atr * self.atr_multiplier),
                "targets": targets
            }
            secondary = {"title": "فشل السيناريو والصعود", "prob": prob_secondary, "target": high, "stop_loss": low - (atr * self.atr_multiplier)}

        if signal == 'HOLD':
            primary['title'] = f"السيناريو المحتمل ({primary['title']})"
            secondary['title'] = f"السيناريو البديل ({secondary['title']})"

        return {"scenario1": primary, "scenario2": secondary}

    def _find_recent_swing_points(self, data: pd.DataFrame) -> (Dict, Dict):
        """
        Finds the most recent valid swing high and swing low based on a simple
        comparison with neighboring candles. A swing high is a candle with a high
        greater than the N candles before and after it. A swing low is the inverse.
        """
        recent_data = data.tail(self.swing_lookback_period).copy()
        window = self.swing_comparison_window

        swing_highs_indices = []
        swing_lows_indices = []

        # Iterate through the data, avoiding the edges where the window doesn't fit
        for i in range(window, len(recent_data) - window):
            # Check for Swing High
            is_swing_high = all(
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i-j] and \
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+j]
                for j in range(1, window + 1)
            )
            if is_swing_high:
                swing_highs_indices.append(recent_data.index[i])

            # Check for Swing Low
            is_swing_low = all(
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i-j] and \
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+j]
                for j in range(1, window + 1)
            )
            if is_swing_low:
                swing_lows_indices.append(recent_data.index[i])

        if not swing_highs_indices or not swing_lows_indices:
            return None, None # Return nothing if no clear swings are found

        # Find the most recent valid pair
        latest_high_idx = swing_highs_indices[-1]
        latest_low_idx = swing_lows_indices[-1]

        if latest_high_idx > latest_low_idx:
            # Last swing was a high. Find the last low before it.
            prior_lows = [idx for idx in swing_lows_indices if idx < latest_high_idx]
            if not prior_lows: return None, None
            final_low_idx = prior_lows[-1]
            final_high_idx = latest_high_idx
        else:
            # Last swing was a low. Find the last high before it.
            prior_highs = [idx for idx in swing_highs_indices if idx < latest_low_idx]
            if not prior_highs: return None, None
            final_high_idx = prior_highs[-1]
            final_low_idx = latest_low_idx

        swing_high = {'price': recent_data.loc[final_high_idx, 'high'], 'index': final_high_idx}
        swing_low = {'price': recent_data.loc[final_low_idx, 'low'], 'index': final_low_idx}

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
        p_high, p_low = self._find_recent_swing_points(data)
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