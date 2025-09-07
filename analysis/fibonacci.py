import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from scipy.signal import find_peaks
import logging

logger = logging.getLogger(__name__)

class FibonacciAnalysis:
    """
    وحدة تحليل فيبوناتشي المتقدمة
    """
    def __init__(self, df: pd.DataFrame, config: dict = None, timeframe: str = '1h'):
        self.df = df.copy()
        if config is None: config = {}
        self.timeframe = timeframe

        overrides = config.get('TIMEFRAME_OVERRIDES', {}).get(timeframe, {})
        self.lookback_period = overrides.get('FIB_LOOKBACK', config.get('FIB_LOOKBACK', 90))

        self.data = self.df.tail(self.lookback_period).reset_index(drop=True)
        self.current_price = self.data['close'].iloc[-1] if not self.data.empty else 0
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_ratios = [1.272, 1.618, 2.0, 2.618]

    def find_major_swing(self) -> Dict:
        """
        Finds the most significant and recent price swing using ATR-based pivots.
        This is more robust and accurate than the previous method.
        """
        if len(self.data) < 20:
            return {}

        # 1. Use ATR for dynamic prominence calculation
        atr_column = next((col for col in self.data.columns if 'ATRr' in col), None)
        if atr_column is None or self.data[atr_column].isnull().all():
            prominence = self.data['close'].std() * 0.8
        else:
            prominence = self.data[atr_column].mean() * 1.0

        if np.isnan(prominence) or prominence == 0:
            logger.warning("Could not calculate valid prominence for pivot detection.")
            return {}

        # 2. Find all pivot points
        distance = 10
        high_pivots_idx, _ = find_peaks(self.data['high'], prominence=prominence, distance=distance)
        low_pivots_idx, _ = find_peaks(-self.data['low'], prominence=prominence, distance=distance)

        if high_pivots_idx.size < 1 or low_pivots_idx.size < 1:
            logger.info("Not enough high/low pivots found for swing analysis.")
            return {}

        # 3. Generate swings
        swings = []
        all_pivots = sorted(
            [(i, 'h') for i in high_pivots_idx] + [(i, 'l') for i in low_pivots_idx],
            key=lambda x: x[0]
        )
        for i in range(1, len(all_pivots)):
            prev_idx, prev_type = all_pivots[i-1]
            curr_idx, curr_type = all_pivots[i]
            if prev_type != curr_type:
                high_idx = curr_idx if curr_type == 'h' else prev_idx
                low_idx = curr_idx if curr_type == 'l' else prev_idx
                swings.append({
                    'high': {'price': self.data['high'].iloc[high_idx], 'time': high_idx},
                    'low': {'price': self.data['low'].iloc[low_idx], 'time': low_idx}
                })

        if not swings:
            logger.info("No valid swings generated from pivots.")
            return {}

        # 4. Select best swing
        best_swing = None
        max_score = -1
        relevance_threshold_index = len(self.data) * (1 - 0.35)
        for swing in swings:
            swing_end_time = max(swing['high']['time'], swing['low']['time'])
            if swing_end_time >= relevance_threshold_index:
                price_range = swing['high']['price'] - swing['low']['price']
                if price_range > max_score:
                    max_score = price_range
                    best_swing = swing

        return best_swing if best_swing else {}

    def get_comprehensive_fibonacci_analysis(self) -> Dict:
        try:
            logger.info(f"Starting Fibonacci analysis with lookback {self.lookback_period}.")
            if len(self.data) < 20:
                logger.warning(f"Not enough data for Fibonacci analysis. Data has {len(self.data)} rows, need 20.")
                return {'error': 'Not enough data for Fibonacci analysis.', 'fib_score': 0}

            swing = self.find_major_swing()

            if not swing:
                logger.warning("find_major_swing returned no swing. Falling back to simple min/max.")
                major_high_price = self.data['high'].max()
                major_low_price = self.data['low'].min()
                major_high_time = self.data['high'].idxmax()
                major_low_time = self.data['low'].idxmin()
                swing = {'high': {'price': major_high_price, 'time': major_high_time}, 'low': {'price': major_low_price, 'time': major_low_time}}

            if not swing:
                logger.error("Could not determine any swing points, even with fallback.")
                return {'error': 'Could not determine swing points.', 'fib_score': 0}

            high, low = swing['high'], swing['low']
            logger.info(f"Found swing: Low at {low['price']:.2f} (t={low['time']}), High at {high['price']:.2f} (t={high['time']}).")
            price_range = high['price'] - low['price']
            if price_range <= 0:
                logger.error(f"Price range is zero or invalid: {price_range}")
                return {'error': 'Price range is zero or invalid.', 'fib_score': 0}

            retracements, extensions = [], []
            if high['time'] > low['time']: # Uptrend swing
                for ratio in self.retracement_ratios: retracements.append({'level': f"{ratio*100:.1f}%", 'price': high['price'] - price_range * ratio})
                for ratio in self.extension_ratios: extensions.append({'level': f"{ratio*100:.1f}%", 'price': high['price'] + price_range * (ratio - 1)})
            else: # Downtrend swing
                for ratio in self.retracement_ratios: retracements.append({'level': f"{ratio*100:.1f}%", 'price': low['price'] + price_range * ratio})
                for ratio in self.extension_ratios: extensions.append({'level': f"{ratio*100:.1f}%", 'price': low['price'] - price_range * (ratio - 1)})

            fib_score = 0
            for r in retracements:
                if abs(self.current_price - r['price']) / self.current_price < 0.015:
                    if r['level'] in ['38.2%', '50.0%', '61.8%']: fib_score += 2
                    else: fib_score += 1

            logger.info(f"Fibonacci analysis complete. Final score: {fib_score}.")
            return {'retracement_levels': retracements, 'extension_levels': extensions, 'fib_score': fib_score}
        except Exception as e:
            logger.exception("An unexpected error occurred during Fibonacci analysis.")
            return {'error': str(e), 'fib_score': 0, 'retracement_levels': [], 'extension_levels': []}
