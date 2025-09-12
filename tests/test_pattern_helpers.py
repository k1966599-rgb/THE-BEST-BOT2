import unittest
import pandas as pd
import numpy as np
from src.analysis.patterns.pattern_helpers import calculate_dynamic_confidence, find_trend_line

class TestPatternHelpers(unittest.TestCase):

    def setUp(self):
        self.config = {'ADX_PERIOD': 14, 'RSI_PERIOD': 14}
        data = {
            'volume': [1000, 1500, 1200, 2500, 1800] * 5,
            'ADX_14': [20, 22, 28, 30, 26] * 5,
            'RSI_14': [60, 65, 72, 78, 68] * 5
        }
        self.df = pd.DataFrame(data)

    def test_calculate_dynamic_confidence_empty_df(self):
        df = pd.DataFrame()
        confidence = calculate_dynamic_confidence(df, self.config, 50, True)
        self.assertEqual(confidence, 50)

    def test_calculate_dynamic_confidence_bullish(self):
        # Make the last volume high enough for bonus
        self.df.loc[self.df.index[-1], 'volume'] = self.df['volume'].mean() * 2
        confidence = calculate_dynamic_confidence(self.df, self.config, 50, True)
        # 50 (base) + 10 (volume) + 10 (ADX > 25) + 5 (RSI < 75) = 75
        self.assertEqual(confidence, 75)

    def test_calculate_dynamic_confidence_bearish(self):
        self.df.loc[self.df.index[-1], 'RSI_14'] = 30
        confidence = calculate_dynamic_confidence(self.df, self.config, 60, False)
        # 60 (base) + 0 (volume) + 10 (ADX > 25) + 5 (RSI > 25) = 75
        self.assertEqual(confidence, 75)

    def test_calculate_dynamic_confidence_capped(self):
        confidence = calculate_dynamic_confidence(self.df, self.config, 90, True)
        # 90 (base) + 0 (volume) + 10 (ADX > 25) + 5 (RSI < 75) = 105, capped at 98
        self.assertEqual(confidence, 98)

    def test_find_trend_line_valid(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10] # y = 2x
        line = find_trend_line(x, y)
        self.assertAlmostEqual(line['slope'], 2.0)
        self.assertAlmostEqual(line['intercept'], 0.0)

    def test_find_trend_line_invalid_input(self):
        line = find_trend_line([], [])
        self.assertEqual(line, {'slope': 0, 'intercept': 0})
        line = find_trend_line([1, 2], [1])
        self.assertEqual(line, {'slope': 0, 'intercept': 0})

if __name__ == '__main__':
    unittest.main()
