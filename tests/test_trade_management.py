import unittest
import pandas as pd
from src.trade_management import TradeManagement

class TestTradeManagement(unittest.TestCase):
    def setUp(self):
        data = {
            'high': [110, 112, 108, 115, 118],
            'low': [100, 105, 102, 106, 110],
            'close': [105, 110, 106, 112, 116]
        }
        self.df = pd.DataFrame(data)
        self.trade_manager = TradeManagement(self.df, account_balance=10000, max_risk_per_trade=0.02)

    def test_initialization(self):
        self.assertIsNotNone(self.trade_manager)
        self.assertEqual(self.trade_manager.account_balance, 10000)
        self.assertEqual(self.trade_manager.max_risk_per_trade, 0.02)
        self.assertEqual(self.trade_manager.current_price, 116)

    def test_calculate_position_size_valid(self):
        position_info = self.trade_manager.calculate_position_size(entry_price=116, stop_loss=110)
        self.assertAlmostEqual(position_info['position_size'], 33.333, places=3)
        self.assertAlmostEqual(position_info['total_value'], 3866.667, places=3)
        self.assertEqual(position_info['risk_per_share'], 6)
        self.assertAlmostEqual(position_info['risk_percentage'], 5.172, places=3)

    def test_calculate_position_size_zero_distance(self):
        position_info = self.trade_manager.calculate_position_size(entry_price=116, stop_loss=116)
        self.assertIn('error', position_info)
        self.assertEqual(position_info['error'], 'Stop-loss cannot be the same as the entry price.')

    def test_calculate_position_size_exceeds_balance(self):
        # High risk to force total_value > account_balance
        self.trade_manager.max_risk_per_trade = 0.5
        position_info = self.trade_manager.calculate_position_size(entry_price=116, stop_loss=115)
        self.assertAlmostEqual(position_info['position_size'], 86.207, places=3)
        self.assertEqual(position_info['total_value'], 10000)

    def test_get_trade_levels_with_sr(self):
        analysis_results = {
            'support_resistance': {
                'nearest_support': {'price': 108},
                'nearest_resistance': {'price': 120}
            }
        }
        levels = self.trade_manager.get_trade_levels(analysis_results)
        self.assertEqual(levels['long_entry'], 116)
        self.assertEqual(levels['long_stop_loss'], 98)
        self.assertEqual(levels['long_profit_target'], 143)
        self.assertEqual(levels['short_entry'], 116)
        self.assertEqual(levels['short_stop_loss'], 134)
        self.assertEqual(levels['short_profit_target'], 89)

    def test_get_trade_levels_no_sr(self):
        analysis_results = {}
        levels = self.trade_manager.get_trade_levels(analysis_results)
        self.assertEqual(levels['long_entry'], 116)
        self.assertEqual(levels['long_stop_loss'], 98)
        self.assertEqual(levels['long_profit_target'], 143.0)
        self.assertEqual(levels['short_entry'], 116)
        self.assertEqual(levels['short_stop_loss'], 134)
        self.assertEqual(levels['short_profit_target'], 89.0)

    def test_get_comprehensive_trade_plan_buy_signal(self):
        final_recommendation = {'main_action': 'Strong Buy'}
        analysis_results = {}
        trade_plan = self.trade_manager.get_comprehensive_trade_plan(final_recommendation, analysis_results)
        self.assertEqual(trade_plan['signal'], 'Strong Buy')
        self.assertEqual(trade_plan['direction'], 'Long')
        self.assertEqual(trade_plan['entry_price'], 116)

    def test_get_comprehensive_trade_plan_sell_signal(self):
        final_recommendation = {'main_action': 'Strong Sell'}
        analysis_results = {}
        trade_plan = self.trade_manager.get_comprehensive_trade_plan(final_recommendation, analysis_results)
        self.assertEqual(trade_plan['signal'], 'Strong Sell')
        self.assertEqual(trade_plan['direction'], 'Short')
        self.assertEqual(trade_plan['entry_price'], 116)

    def test_get_comprehensive_trade_plan_wait_signal(self):
        final_recommendation = {'main_action': 'Wait'}
        analysis_results = {}
        trade_plan = self.trade_manager.get_comprehensive_trade_plan(final_recommendation, analysis_results)
        self.assertEqual(trade_plan['signal'], 'Wait')
        self.assertEqual(trade_plan['recommendation'], "No trade setup at the moment. Monitor the market.")

    def test_get_comprehensive_trade_plan_wait_signal_bullish_pattern(self):
        final_recommendation = {'main_action': 'Wait'}
        analysis_results = {
            'patterns': {
                'found_patterns': [{
                    'name': 'Bullish Pattern',
                    'status': 'Forming',
                    'is_bullish': True,
                    'resistance_line': 120,
                    'support_line': 110,
                    'calculated_target': 130
                }]
            }
        }
        trade_plan = self.trade_manager.get_comprehensive_trade_plan(final_recommendation, analysis_results)
        self.assertEqual(trade_plan['trade_idea_name'], 'Monitor for breakout of Bullish Pattern pattern')
        self.assertEqual(trade_plan['conditional_entry'], 120)

    def test_get_comprehensive_trade_plan_wait_signal_bearish_pattern(self):
        final_recommendation = {'main_action': 'Wait'}
        analysis_results = {
            'patterns': {
                'found_patterns': [{
                    'name': 'Bearish Pattern',
                    'status': 'Forming',
                    'is_bullish': False,
                    'resistance_line': 120,
                    'support_line': 110,
                    'calculated_target': 100
                }]
            }
        }
        trade_plan = self.trade_manager.get_comprehensive_trade_plan(final_recommendation, analysis_results)
        self.assertEqual(trade_plan['trade_idea_name'], 'Monitor for breakdown of Bearish Pattern pattern')
        self.assertEqual(trade_plan['conditional_entry'], 110)

    def test_correct_atr_calculation(self):
        """
        Tests that the get_trade_levels function uses the correct ATR calculation.
        """
        data = {
            'high': [110, 112, 108, 115, 118, 120, 122, 118, 121, 125, 123, 126, 122, 128, 130, 127, 132, 135, 133, 138],
            'low': [100, 105, 102, 106, 110, 112, 115, 114, 118, 120, 119, 121, 118, 124, 126, 123, 128, 130, 129, 132],
            'close': [105, 110, 106, 112, 116, 118, 120, 116, 120, 124, 121, 125, 120, 127, 128, 125, 130, 133, 130, 136]
        }
        df = pd.DataFrame(data)
        trade_manager = TradeManagement(df)

        # With the correct ATR calculation, the last ATR value is approx 6.495
        # The current price is 136.
        # long_stop_loss = 136 - 6.495 = 129.505
        levels = trade_manager.get_trade_levels({})
        self.assertAlmostEqual(levels['long_stop_loss'], 129.50, places=2)


if __name__ == '__main__':
    unittest.main()
