import pandas as pd
import logging
from typing import Dict, Any, List
from scipy.signal import find_peaks
from src.data_retrieval.data_fetcher import DataFetcher

from src.strategies.base_strategy import BaseStrategy
from src.strategies.exceptions import InsufficientDataError
from src.utils.indicators import (
    calculate_sma, calculate_fib_levels,
    calculate_fib_extensions, calculate_rsi, calculate_macd,
    calculate_stochastic, calculate_bollinger_bands, calculate_adx,
    calculate_atr
)
from src.utils.patterns import get_candlestick_pattern

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
        self.trend_confirmation_multiplier = p.get('trend_confirmation_multiplier', 1.5)
        self.mta_confidence_modifier = p.get('mta_confidence_modifier', 20) # Percentage modifier

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

    def _calculate_confirmation_score(self, data: pd.DataFrame, fibo_trend: str, main_trend: str) -> Dict[str, Any]:
        score, reasons = 0, []
        data['volume_sma'] = data['volume'].rolling(window=self.volume_period).mean()
        latest = data.iloc[-1]

        # Determine the multiplier if the signal aligns with the main trend
        trend_aligned = (fibo_trend == main_trend)
        multiplier = self.trend_confirmation_multiplier if trend_aligned else 1.0

        bullish_patterns = ["Bullish Engulfing", "Hammer", "Morning Star", "Piercing Pattern", "Three White Soldiers", "Tweezer Bottom"]
        bearish_patterns = ["Bearish Engulfing", "Shooting Star", "Evening Star", "Dark Cloud Cover", "Three Black Crows", "Tweezer Top"]
        pattern = get_candlestick_pattern(data.tail(3))

        # Each reason is a dict with a key for localization and optional context
        if fibo_trend == 'up':
            if latest['rsi'] > 50:
                score += self.weights.get('rsi_confirm', 1) * multiplier
                reasons.append({'key': 'reason_rsi_confirm_up', 'context': {'value': f"{latest['rsi']:.2f}"}})
            if latest['macd'] > latest['signal_line']:
                score += self.weights.get('macd_confirm', 1) * multiplier
                reasons.append({'key': 'reason_macd_confirm_up'})
            if latest['stoch_k'] < 30 and latest['stoch_k'] > latest['stoch_d']:
                score += self.weights.get('stoch_confirm', 1) # Stochastic is an oscillator, not trend-dependent
                reasons.append({'key': 'reason_stoch_confirm_up'})
            if pattern in bullish_patterns:
                score += self.weights.get('reversal_pattern', 2) * multiplier
                reasons.append({'key': 'reason_pattern_confirm_up', 'context': {'pattern': pattern}})
        else: # 'down'
            if latest['rsi'] < 50:
                score += self.weights.get('rsi_confirm', 1) * multiplier
                reasons.append({'key': 'reason_rsi_confirm_down', 'context': {'value': f"{latest['rsi']:.2f}"}})
            if latest['macd'] < latest['signal_line']:
                score += self.weights.get('macd_confirm', 1) * multiplier
                reasons.append({'key': 'reason_macd_confirm_down'})
            if latest['stoch_k'] > 70 and latest['stoch_k'] < latest['stoch_d']:
                score += self.weights.get('stoch_confirm', 1) # Stochastic is an oscillator
                reasons.append({'key': 'reason_stoch_confirm_down'})
            if pattern in bearish_patterns:
                score += self.weights.get('reversal_pattern', 2) * multiplier
                reasons.append({'key': 'reason_pattern_confirm_down', 'context': {'pattern': pattern}})

        volume_threshold = latest['volume_sma'] * self.volume_spike_multiplier
        if latest['volume'] > volume_threshold:
            if fibo_trend == 'up' and latest['close'] > latest['open']:
                score += self.weights.get('volume_spike', 2) * multiplier
                reasons.append({'key': 'reason_volume_confirm_up'})
            elif fibo_trend == 'down' and latest['close'] < latest['open']:
                score += self.weights.get('volume_spike', 2) * multiplier
                reasons.append({'key': 'reason_volume_confirm_down'})

        return {"score": score, "reasons": reasons, "pattern": pattern}

    def _calculate_risk_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        score = result.get('score', 0)
        max_score = sum(self.weights.values())

        # Base confidence score
        base_confidence = round(50 + (score / max_score) * 45 if max_score > 0 else 50)

        # Modify confidence based on MTA sentiment
        mta_sentiment = result.get('mta_sentiment', 'neutral')
        if mta_sentiment == 'aligned':
            final_confidence = min(100, base_confidence + self.mta_confidence_modifier)
        elif mta_sentiment == 'conflicting':
            final_confidence = max(0, base_confidence - self.mta_confidence_modifier)
        else:
            final_confidence = base_confidence

        result['confidence'] = final_confidence

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
                "title_key": "scenario_title_up_primary", "prob": prob_primary,
                "entry_zone": entry_zone,
                "stop_loss": low - (atr * self.atr_multiplier),
                "targets": targets
            }
            secondary = {"title_key": "scenario_title_up_secondary", "prob": prob_secondary, "target": low, "stop_loss": high + (atr * self.atr_multiplier)}
        else: # 'down'
            primary = {
                "title_key": "scenario_title_down_primary", "prob": prob_primary,
                "entry_zone": entry_zone,
                "stop_loss": high + (atr * self.atr_multiplier),
                "targets": targets
            }
            secondary = {"title_key": "scenario_title_down_secondary", "prob": prob_secondary, "target": high, "stop_loss": low - (atr * self.atr_multiplier)}

        if signal == 'HOLD':
            primary['title_key'] += '_hold'
            secondary['title_key'] += '_hold'

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
            result['reason_key'] = "error_no_valid_swings"
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

        confirm_data = self._calculate_confirmation_score(data, fibo_trend, result['trend'])
        result.update(confirm_data)

        score_met = result['score'] >= self.signal_threshold
        adx_value = result.get('latest_data', {}).get('adx', 0)
        adx_confirmed = not self.require_adx_confirmation or (adx_value >= self.adx_threshold)

        if score_met and adx_confirmed:
            result['signal'] = "BUY" if fibo_trend == 'up' else "SELL"
            result['final_reason'] = {'key': 'final_reason_signal_confirmed', 'context': {'score': result['score'], 'trend': fibo_trend}}
        elif score_met and not adx_confirmed:
            result['final_reason'] = {'key': 'final_reason_score_met_adx_weak', 'context': {'adx': f"{adx_value:.2f}"}}
        else:
            result['final_reason'] = {'key': 'final_reason_score_not_met', 'context': {'score': result['score'], 'threshold': self.signal_threshold}}

        # --- MTA Sentiment Analysis ---
        # Determine if the signal aligns with, conflicts with, or is neutral to the higher timeframe trend.
        result['mta_sentiment'] = 'neutral'
        higher_tf_trend_info = result.get('higher_tf_trend_info')
        if higher_tf_trend_info and result['signal'] != 'HOLD':
            higher_trend = higher_tf_trend_info.get('trend')

            # Check for alignment
            if (result['signal'] == 'BUY' and higher_trend == 'up') or \
               (result['signal'] == 'SELL' and higher_trend == 'down'):
                result['mta_sentiment'] = 'aligned'
                result['reasons'].append({'key': 'reason_mta_aligned'})
            # Check for conflict
            elif (result['signal'] == 'BUY' and higher_trend == 'down') or \
                 (result['signal'] == 'SELL' and higher_trend == 'up'):
                result['mta_sentiment'] = 'conflicting'
                result['reasons'].append({'key': 'reason_mta_conflicting'})

    def _finalize_analysis(self, result: Dict):
        result['scenarios'] = self._generate_scenarios(result)
        self._calculate_risk_metrics(result)
        self._identify_key_levels(result)

    def _identify_key_levels(self, result: Dict):
        """
        Identifies and adds key support and resistance levels to the result,
        including the single most important support and resistance with their types.
        """
        levels = []
        swing_high = result.get('swing_high', {}).get('price')
        swing_low = result.get('swing_low', {}).get('price')
        retracements = result.get('retracements', {})
        current_price = result.get('current_price', 0)

        if swing_high: levels.append({'level': swing_high, 'type': 'قمة سابقة'})
        if swing_low: levels.append({'level': swing_low, 'type': 'قاع سابق'})

        fib_levels_to_add = ['fib_382', 'fib_500', 'fib_618']
        for key in fib_levels_to_add:
            level_value = retracements.get(key)
            if level_value:
                level_ratio = key.replace('fib_', '0.')
                levels.append({'level': level_value, 'type': f"فيبوناتشي {level_ratio}"})

        # Sort levels by price to make finding support/resistance easier
        levels.sort(key=lambda x: x['level'])

        # Find first level below current price (support) and first above (resistance)
        key_support_dict = next((lvl for lvl in reversed(levels) if lvl['level'] < current_price), None)
        key_resistance_dict = next((lvl for lvl in levels if lvl['level'] > current_price), None)

        result['key_levels'] = levels

        # Store the full dictionary for key support and resistance, with fallbacks
        if key_support_dict:
            result['key_support'] = key_support_dict
        else:
            result['key_support'] = {'level': swing_low, 'type': 'قاع سابق'} if swing_low else {}

        if key_resistance_dict:
            result['key_resistance'] = key_resistance_dict
        else:
            result['key_resistance'] = {'level': swing_high, 'type': 'قمة سابقة'} if swing_high else {}

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
            # The reason_key is already set in _analyze_trend_and_swings
            return result

        self._analyze_fibonacci_and_score(data, result)
        self._finalize_analysis(result)
        result['weights'] = self.weights
        return result