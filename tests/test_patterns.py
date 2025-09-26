import unittest
import pandas as pd
from src.utils.patterns import (
    is_three_white_soldiers, is_three_black_crows,
    is_tweezer_bottom, is_tweezer_top
)

class TestCandlestickPatterns(unittest.TestCase):

    def test_is_three_white_soldiers_positive(self):
        """Test for a valid Three White Soldiers pattern."""
        data = pd.DataFrame({
            'open':  [100, 101, 103],
            'high':  [105, 106, 108],
            'low':   [99,  100, 102],
            'close': [104, 105, 107]
        })
        self.assertTrue(is_three_white_soldiers(data))

    def test_is_three_white_soldiers_negative_not_all_bullish(self):
        """Test fails if one candle is bearish."""
        data = pd.DataFrame({
            'open':  [100, 101, 106], # Third candle is bearish
            'high':  [105, 106, 108],
            'low':   [99,  100, 102],
            'close': [104, 105, 105]
        })
        self.assertFalse(is_three_white_soldiers(data))

    def test_is_three_white_soldiers_negative_wrong_open(self):
        """Test fails if a candle opens outside the previous body."""
        data = pd.DataFrame({
            'open':  [100, 105, 106], # Second candle opens above previous close
            'high':  [105, 108, 109],
            'low':   [99,  104, 105],
            'close': [104, 107, 108]
        })
        self.assertFalse(is_three_white_soldiers(data))

    def test_is_three_white_soldiers_negative_wrong_close(self):
        """Test fails if a candle does not close higher."""
        data = pd.DataFrame({
            'open':  [100, 101, 103],
            'high':  [105, 106, 108],
            'low':   [99,  100, 102],
            'close': [104, 103, 107] # Second candle closes lower
        })
        self.assertFalse(is_three_white_soldiers(data))

    def test_is_three_black_crows_positive(self):
        """Test for a valid Three Black Crows pattern."""
        data = pd.DataFrame({
            'open':  [110, 108, 106],
            'high':  [111, 109, 107],
            'low':   [105, 103, 101],
            'close': [107, 105, 102]
        })
        self.assertTrue(is_three_black_crows(data))

    def test_is_three_black_crows_negative_not_all_bearish(self):
        """Test fails if one candle is bullish."""
        data = pd.DataFrame({
            'open':  [110, 108, 105], # Third candle is bullish
            'high':  [111, 109, 107],
            'low':   [105, 103, 101],
            'close': [107, 105, 106]
        })
        self.assertFalse(is_three_black_crows(data))

    def test_is_tweezer_bottom_positive(self):
        """Test for a valid Tweezer Bottom pattern."""
        data = pd.DataFrame({
            'open':  [105, 100], # c1 bearish, c2 bullish
            'high':  [106, 104],
            'low':   [99, 99.01], # Lows are nearly equal
            'close': [100, 103]
        })
        self.assertTrue(is_tweezer_bottom(data))

    def test_is_tweezer_bottom_negative_wrong_candles(self):
        """Test fails if candles are not bearish then bullish."""
        data = pd.DataFrame({
            'open':  [100, 100], # Both bullish
            'high':  [106, 104],
            'low':   [99, 99.01],
            'close': [105, 103]
        })
        self.assertFalse(is_tweezer_bottom(data))

    def test_is_tweezer_bottom_negative_unequal_lows(self):
        """Test fails if lows are not nearly equal."""
        data = pd.DataFrame({
            'open':  [105, 100],
            'high':  [106, 104],
            'low':   [99, 95], # Lows are too far apart
            'close': [100, 103]
        })
        self.assertFalse(is_tweezer_bottom(data))

    def test_is_tweezer_top_positive(self):
        """Test for a valid Tweezer Top pattern."""
        data = pd.DataFrame({
            'open':  [100, 105], # c1 bullish, c2 bearish
            'high':  [106, 105.99], # Highs are nearly equal
            'low':   [99, 102],
            'close': [105, 103]
        })
        self.assertTrue(is_tweezer_top(data))

    def test_is_tweezer_top_negative_wrong_candles(self):
        """Test fails if candles are not bullish then bearish."""
        data = pd.DataFrame({
            'open':  [105, 105], # Both bearish
            'high':  [106, 105.99],
            'low':   [99, 102],
            'close': [100, 103]
        })
        self.assertFalse(is_tweezer_top(data))

    def test_is_tweezer_top_negative_unequal_highs(self):
        """Test fails if highs are not nearly equal."""
        data = pd.DataFrame({
            'open':  [100, 105],
            'high':  [106, 110], # Highs are too far apart
            'low':   [99, 102],
            'close': [105, 103]
        })
        self.assertFalse(is_tweezer_top(data))

if __name__ == '__main__':
    unittest.main()