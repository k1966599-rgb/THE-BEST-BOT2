import pandas as pd
import numpy as np
from typing import Dict, List, Any
from abc import ABC, abstractmethod
from sklearn.linear_model import LinearRegression

class BasePattern(ABC):
    """Abstract base class for all pattern detection classes.

    This class provides a common structure and shared helper methods for
    various technical pattern detectors, including trend line calculation,
    pivot filtering, volume analysis, and confidence scoring.
    """
    def __init__(self, df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict],
                 current_price: float, price_tolerance: float, timeframe: str = None, trend_context: dict = None):
        """Initializes the BasePattern.

        Args:
            df (pd.DataFrame): The market data DataFrame.
            config (dict): Configuration settings.
            highs (List[Dict]): A list of pivot high points.
            lows (List[Dict]): A list of pivot low points.
            current_price (float): The current market price.
            price_tolerance (float): The tolerance for price comparisons.
            timeframe (str, optional): The timeframe of the data. Defaults to None.
            trend_context (dict, optional): Context about the preceding trend.
                Defaults to None.
        """
        self.df = df
        self.config = config
        self.highs = highs
        self.lows = lows
        self.current_price = current_price
        self.price_tolerance = price_tolerance
        self.timeframe = timeframe
        self.trend_context = trend_context or {}
        self.found_patterns = []

    @abstractmethod
    def check(self) -> List[Dict]:
        """Checks for the specific pattern.

        This method must be implemented by each subclass to define the logic
        for detecting its specific technical pattern.

        Raises:
            NotImplementedError: If the subclass does not implement this method.

        Returns:
            List[Dict]: A list of found pattern dictionaries.
        """
        pass

    def find_trend_line(self, x_values: List[int], y_values: List[float]) -> Dict:
        """Finds a trend line using linear regression.

        Args:
            x_values (List[int]): The x-coordinates (e.g., time indices).
            y_values (List[float]): The y-coordinates (e.g., prices).

        Returns:
            Dict: A dictionary containing the 'slope', 'intercept', and
            'r_squared' value of the fitted line.
        """
        if len(x_values) < 2 or len(y_values) < 2:
            return {'slope': 0, 'intercept': 0, 'r_squared': 0}

        x_array = np.array(x_values).reshape(-1, 1)
        y_array = np.array(y_values)

        reg = LinearRegression().fit(x_array, y_array)
        r_squared = reg.score(x_array, y_array)

        return {
            'slope': reg.coef_[0],
            'intercept': reg.intercept_,
            'r_squared': r_squared
        }

    def _filter_pivots(self, search_window_bars: int) -> (List[Dict], List[Dict]):
        """Filters the pivot points to a specific search window.

        Args:
            search_window_bars (int): The number of recent bars to include in
                the search window.

        Returns:
            tuple: A tuple containing two lists: filtered pivot highs and
            filtered pivot lows.
        """
        search_window = min(search_window_bars, len(self.df) // 2)
        search_data = self.df.tail(search_window)
        window_highs = [h for h in self.highs if h['index'] >= search_data.index[0]]
        window_lows = [l for l in self.lows if l['index'] >= search_data.index[0]]
        return window_highs, window_lows

    def _calculate_trend_lines(self, window_highs: List[Dict], window_lows: List[Dict]) -> (Dict, Dict):
        """Calculates the trend lines for the given pivot points.

        This method is not implemented in the base class and should be
        implemented by subclasses if needed. The base implementation is a
        placeholder.
        """
        # This is a placeholder and might need to be adapted if find_trend_line is a global function
        upper_trend = self.find_trend_line([p['index'] for p in window_highs], [p['price'] for p in window_highs])
        lower_trend = self.find_trend_line([p['index'] for p in window_lows], [p['price'] for p in window_lows])
        return upper_trend, lower_trend

    def _get_current_levels(self, upper_trend: Dict, lower_trend: Dict) -> (float, float):
        """Calculates the current resistance and support levels from trend lines.

        Args:
            upper_trend (Dict): The equation of the upper trend line.
            lower_trend (Dict): The equation of the lower trend line.

        Returns:
            tuple: A tuple containing the projected resistance and support
            levels at the current time index.
        """
        current_index = len(self.df) - 1
        resistance_current = upper_trend['slope'] * current_index + upper_trend['intercept']
        support_current = lower_trend['slope'] * current_index + lower_trend['intercept']
        return resistance_current, support_current

    def _analyze_volume(self, start_index: int, boundary_levels: List[float]) -> Dict:
        """Analyzes volume characteristics for the pattern.

        Args:
            start_index (int): The starting index of the pattern formation.
            boundary_levels (List[float]): A list of key price levels that
                form the pattern's boundaries.

        Returns:
            Dict: A dictionary containing volume analysis metrics.
        """
        volume_analysis = {}
        if 'volume' not in self.df.columns:
            return {}

        pattern_df = self.df.loc[start_index:]
        avg_volume = pattern_df['volume'].mean()
        if avg_volume == 0: return {}

        # 1. Volume Decline Analysis
        early_volume = pattern_df['volume'].iloc[:len(pattern_df)//2].mean()
        late_volume = pattern_df['volume'].iloc[len(pattern_df)//2:].mean()
        volume_analysis['volume_decline'] = early_volume > late_volume * 1.2

        # 2. Breakout Volume Strength
        volume_analysis['breakout_volume'] = self.df.iloc[-1]['volume'] / avg_volume

        # 3. Boundary Strength Analysis
        total_boundary_volume = 0
        tolerance = self.current_price * 0.01 # 1% tolerance for zone
        for level in boundary_levels:
            zone_df = self.df[(self.df['low'] <= level + tolerance) & (self.df['high'] >= level - tolerance)]
            total_boundary_volume += zone_df['volume'].sum()

        # Normalize the boundary volume against the total volume in the pattern
        total_pattern_volume = pattern_df['volume'].sum()
        if total_pattern_volume > 0:
            # Score from 0 to 100
            boundary_strength = min(100, (total_boundary_volume / total_pattern_volume) * 100)
        else:
            boundary_strength = 0
        volume_analysis['boundary_strength'] = boundary_strength

        return volume_analysis

    def _calculate_confidence(self, **kwargs) -> float:
        """Calculates a confidence score based on various weighted metrics.

        This method computes a score from 30 to 95 based on factors like
        the quality of trend line fits (R-squared), the number of pivot
        touches, volume confirmation, and alignment with the broader market
        trend.

        Args:
            **kwargs: A dictionary of metrics to be used in the calculation.
                Expected keys include 'r_squared_upper', 'r_squared_lower',
                'touch_count', 'volume_confirmation', and 'pattern_is_bullish'.

        Returns:
            float: The calculated confidence score.
        """
        base_confidence = 50.0
        total_weight = 0
        weighted_score = 0

        # R-squared of trendlines
        if 'r_squared_upper' in kwargs and 'r_squared_lower' in kwargs:
            r_squared_avg = (kwargs['r_squared_upper'] + kwargs['r_squared_lower']) / 2
            weighted_score += r_squared_avg * 15 # Weight of 15
            total_weight += 15

        # Number of pivot touches
        if 'touch_count' in kwargs:
            # Score based on number of touches above the minimum (e.g., 4)
            touch_score = max(0, (kwargs['touch_count'] - 4) * 5)
            weighted_score += min(touch_score, 20) # Max score of 20
            total_weight += 20

        # Volume confirmation (declining volume during formation)
        if 'volume_confirmation' in kwargs and kwargs['volume_confirmation']:
            weighted_score += 15 # Weight of 15
            total_weight += 15

        # Boundary strength (volume at S/R levels)
        if 'boundary_strength' in kwargs:
            # boundary_strength is expected to be a score from 0-100
            weighted_score += kwargs['boundary_strength'] * 0.25 # Weight of 25
            total_weight += 25

        # Trend alignment
        if 'pattern_is_bullish' in kwargs and self.trend_context.get('trend_direction') == 'Uptrend':
            if kwargs['pattern_is_bullish']:
                weighted_score += 30 # Major boost for trend alignment
            else:
                weighted_score -= 15 # Penalty for counter-trend pattern
            total_weight += 30
        elif 'pattern_is_bullish' in kwargs and self.trend_context.get('trend_direction') == 'Downtrend':
            if not kwargs['pattern_is_bullish']:
                weighted_score += 30 # Major boost for trend alignment
            else:
                weighted_score -= 15 # Penalty for counter-trend pattern
            total_weight += 30

        # Add other metrics here...

        if total_weight == 0:
            return base_confidence

        # Normalize the weighted score to be out of 100
        normalized_score = (weighted_score / total_weight) * 100

        # Blend with base confidence
        final_confidence = (base_confidence * 0.4) + (normalized_score * 0.6)

        return min(95.0, max(30.0, final_confidence))

    def _calculate_atr_stop_loss(self, price_level: float, atr_multiplier: float = 2.0, is_long: bool = True) -> float:
        """Calculates a stop-loss level based on ATR.

        Args:
            price_level (float): The price level to base the stop-loss on (e.g., a pivot low).
            atr_multiplier (float, optional): The multiplier for the ATR value. Defaults to 2.0.
            is_long (bool, optional): True for a long position (stop below price), False for short. Defaults to True.

        Returns:
            float: The calculated stop-loss price.
        """
        atr_col = f"ATRr_{self.config.get('ATR_PERIOD', 14)}"
        if atr_col.lower() not in self.df.columns and atr_col.upper() not in self.df.columns:
            # Fallback to a fixed percentage if ATR is not available
            return price_level * 0.99 if is_long else price_level * 1.01

        atr_value = self.df.iloc[-1].get(atr_col.upper(), self.df.iloc[-1].get(atr_col.lower()))

        if is_long:
            return price_level - (atr_value * atr_multiplier)
        else:
            return price_level + (atr_value * atr_multiplier)
