import unittest
import pandas as pd
import numpy as np
from src.analysis.new_support_resistance import find_new_support_resistance
from src.analysis.data_models import Level

class TestNewSupportResistance(unittest.TestCase):

    def setUp(self):
        # Sample data that should generate some peaks
        data = {
            'high': [100, 105, 102, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 120, 110],
            'low': [90, 95, 92, 100, 98, 105, 102, 110, 108, 115, 112, 120, 118, 115, 100],
            'close': [95, 102, 98, 108, 105, 112, 110, 118, 115, 122, 120, 128, 125, 118, 105]
        }
        self.df = pd.DataFrame(data)

    def test_find_new_support_resistance_valid_data(self):
        result = find_new_support_resistance(self.df)
        self.assertIn('supports', result)
        self.assertIn('resistances', result)
        self.assertIsInstance(result['supports'], list)
        self.assertIsInstance(result['resistances'], list)
        self.assertGreater(len(result['supports']), 0)
        self.assertGreater(len(result['resistances']), 0)
        self.assertIsInstance(result['supports'][0], Level)
        self.assertIsInstance(result['resistances'][0], Level)

    def test_find_new_support_resistance_empty_df(self):
        df = pd.DataFrame()
        result = find_new_support_resistance(df)
        self.assertEqual(result, {'supports': [], 'resistances': []})

    def test_find_new_support_resistance_zero_price_range(self):
        data = {
            'high': [100, 100, 100, 100],
            'low': [100, 100, 100, 100],
            'close': [100, 100, 100, 100]
        }
        df = pd.DataFrame(data)
        result = find_new_support_resistance(df)
        self.assertEqual(result, {'supports': [], 'resistances': []})

    def test_find_new_support_resistance_no_peaks(self):
        # Linearly increasing data should not have peaks
        data = {
            'high': np.arange(100, 120),
            'low': np.arange(90, 110),
            'close': np.arange(95, 115)
        }
        df = pd.DataFrame(data)
        result = find_new_support_resistance(df)
        # Should still have historical high/low
        self.assertEqual(len(result['supports']), 1)
        self.assertEqual(len(result['resistances']), 1)
        self.assertEqual(result['supports'][0].name, 'دعم تاريخي')
        self.assertEqual(result['resistances'][0].name, 'مقاومة تاريخية')

if __name__ == '__main__':
    unittest.main()
