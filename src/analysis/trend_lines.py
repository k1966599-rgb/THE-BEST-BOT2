import pandas as pd
import logging
from scipy.signal import find_peaks
from typing import Dict, Any, Optional, List
from .base_analysis import BaseAnalysis
from .data_models import Level

logger = logging.getLogger(__name__)

def get_line_equation(p1: tuple, p2: tuple) -> Optional[Dict[str, float]]:
    """Calculates the slope and intercept of a line defined by two points.

    Args:
        p1 (tuple): The first point (x1, y1).
        p2 (tuple): The second point (x2, y2).

    Returns:
        Optional[Dict[str, float]]: A dictionary with 'slope' and 'intercept',
        or None if the line is vertical.
    """
    x1, y1 = p1
    x2, y2 = p2
    if x2 == x1: return None
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return {'slope': slope, 'intercept': intercept}

class TrendLineAnalysis(BaseAnalysis):
    """Analyzes and identifies trend lines from price data.

    This class finds recent pivot highs and lows to construct support and
    resistance trend lines, then projects them to the current time to act as
    dynamic levels.
    """
    def __init__(self, config: dict = None, timeframe: str = None):
        """Initializes the TrendLineAnalysis module.

        Args:
            config (dict, optional): Configuration dictionary. Defaults to None.
            timeframe (str, optional): The timeframe for analysis. Defaults to None.
        """
        super().__init__(config, timeframe)
        self.long_period = self.config.get('TREND_LONG_PERIOD', 100)

    def _get_trend_lines(self, data: pd.DataFrame, highs: List[Dict], lows: List[Dict]) -> (dict, dict):
        """
        Finds the best-fit support and resistance trend lines using multi-touch validation.
        """

        def find_best_line(pivots: List[Dict], is_support: bool):
            best_line = None
            max_touches = 0

            # Ensure pivots are sorted by index
            pivots = sorted(pivots, key=lambda p: p['index'])

            if len(pivots) < 2:
                return None

            # Create numeric index for regression
            x_numeric = list(range(len(data)))
            data['x_numeric'] = x_numeric

            for i in range(len(pivots)):
                for j in range(i + 1, len(pivots)):
                    p1 = pivots[i]
                    p2 = pivots[j]

                    # Get numeric x-coordinates for p1 and p2
                    p1_x_numeric = data.loc[p1['index']]['x_numeric']
                    p2_x_numeric = data.loc[p2['index']]['x_numeric']

                    equation = get_line_equation((p1_x_numeric, p1['price']), (p2_x_numeric, p2['price']))
                    if not equation: continue

                    touches = 2
                    for k in range(len(pivots)):
                        if k == i or k == j: continue
                        pk = pivots[k]
                        pk_x_numeric = data.loc[pk['index']]['x_numeric']

                        projected_price = equation['slope'] * pk_x_numeric + equation['intercept']

                        # Validate with a tolerance
                        if abs(projected_price - pk['price']) / pk['price'] < 0.015: # 1.5% tolerance
                            touches += 1

                    if touches > max_touches:
                        # Further validation: ensure price doesn't cross the line
                        line_is_valid = True
                        sliced_df = data.loc[p1['index']:p2['index']]
                        for index, row in sliced_df.iterrows():
                            projected_price = equation['slope'] * row['x_numeric'] + equation['intercept']
                            if is_support and row['low'] < projected_price:
                                line_is_valid = False
                                break
                            if not is_support and row['high'] > projected_price:
                                line_is_valid = False
                                break

                        if line_is_valid:
                            max_touches = touches
                            best_line = equation

            data.drop(columns=['x_numeric'], inplace=True)
            return best_line

        support_trend = find_best_line(lows, is_support=True)
        resistance_trend = find_best_line(highs, is_support=False)

        return support_trend, resistance_trend

    def _get_trend_name(self) -> str:
        """Returns the trend name based on the timeframe."""
        if self.timeframe == '1d':
            return "طويل المدى"
        if self.timeframe == '4h':
            return "متوسط المدى"
        return "قصير المدى"

    def analyze(self, df: pd.DataFrame, highs: List[Dict], lows: List[Dict]) -> Dict[str, List[Level]]:
        """Identifies dynamic support and resistance levels from trend lines.

        This method uses pre-calculated pivots to create trend lines and then
        calculates the current price levels of these lines to serve as dynamic
        support and resistance.

        Args:
            df (pd.DataFrame): The DataFrame containing market data.
            highs (List[Dict]): A list of pivot high points.
            lows (List[Dict]): A list of pivot low points.

        Returns:
            Dict[str, List[Level]]: A dictionary containing lists of support
            and resistance Level objects derived from the trend lines.
        """
        data = df.tail(self.long_period)
        if len(data) < 20:
            return {'supports': [], 'resistances': []}

        # Filter pivots to be within the current data slice
        highs_in_slice = [h for h in highs if h['index'] in data.index]
        lows_in_slice = [l for l in lows if l['index'] in data.index]

        logger.info(f"TrendLineAnalysis for {self.timeframe}: Analyzing {len(lows_in_slice)} low pivots and {len(highs_in_slice)} high pivots.")
        support_trend, resistance_trend = self._get_trend_lines(data, highs_in_slice, lows_in_slice)

        supports = []
        resistances = []
        current_price = data['close'].iloc[-1]
        if pd.api.types.is_datetime64_any_dtype(data.index):
            current_time_x = data.index[-1].value
        else:
            current_time_x = data.index[-1]

        if support_trend:
            support_price = support_trend['slope'] * current_time_x + support_trend['intercept']
            if support_price < current_price:
                trend_name = self._get_trend_name()
                template_key = f"confluence_{trend_name.replace(' ', '_')}_trend_support"
                supports.append(Level(name=f"دعم الاتجاه {trend_name}", value=round(support_price, 4), level_type='support', quality='حرج', template_key=template_key))

        if resistance_trend:
            resistance_price = resistance_trend['slope'] * current_time_x + resistance_trend['intercept']
            if resistance_price > current_price:
                trend_name = self._get_trend_name()
                template_key = f"confluence_{trend_name.replace(' ', '_')}_trend_resistance"
                resistances.append(Level(name=f"مقاومة الاتجاه {trend_name}", value=round(resistance_price, 4), level_type='resistance', quality='حرج', template_key=template_key))

        return {'supports': supports, 'resistances': resistances}
