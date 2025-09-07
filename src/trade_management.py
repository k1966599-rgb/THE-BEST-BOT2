import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import warnings

warnings.filterwarnings('ignore')

class TradeManagement:
    """وحدة إدارة الصفقات الشاملة"""

    def __init__(self, df: pd.DataFrame, account_balance: float = 10000,
                 max_risk_per_trade: float = 0.02):
        self.df = df.copy()
        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.current_price = df['close'].iloc[-1]

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> Dict[str, Any]:
        """حساب حجم المركز بناءً على إدارة المخاطر"""
        risk_amount = self.account_balance * self.max_risk_per_trade
        distance_to_stop = abs(entry_price - stop_loss)

        if distance_to_stop == 0:
            return {'error': 'وقف الخسارة لا يمكن أن يكون نفس سعر الدخول'}

        position_size = risk_amount / distance_to_stop
        total_value = position_size * entry_price

        # التأكد من أن قيمة المركز لا تتجاوز الرصيد
        if total_value > self.account_balance:
            position_size = self.account_balance / entry_price
            total_value = self.account_balance

        return {
            'position_size': position_size,
            'total_value': total_value,
            'risk_per_share': distance_to_stop,
            'risk_percentage': (distance_to_stop / entry_price) * 100
        }

    def get_trade_levels(self, analysis_results: Dict) -> Dict[str, Any]:
        """تحديد مستويات الدخول، وقف الخسارة، وجني الأرباح"""
        sr_analysis = analysis_results.get('support_resistance', {})
        nearest_support = sr_analysis.get('nearest_support', {}).get('price')
        nearest_resistance = sr_analysis.get('nearest_resistance', {}).get('price')

        atr = self.df['high'].iloc[-14:].max() - self.df['low'].iloc[-14:].min()

        # تحديد وقف الخسارة
        long_stop_loss = self.current_price - atr
        if nearest_support and nearest_support < self.current_price:
            long_stop_loss = min(long_stop_loss, nearest_support * 0.995)

        short_stop_loss = self.current_price + atr
        if nearest_resistance and nearest_resistance > self.current_price:
            short_stop_loss = max(short_stop_loss, nearest_resistance * 1.005)

        # تحديد أهداف الربح
        long_target = self.current_price + (atr * 1.5)
        if nearest_resistance and nearest_resistance > self.current_price:
            long_target = max(long_target, nearest_resistance)

        short_target = self.current_price - (atr * 1.5)
        if nearest_support and nearest_support < self.current_price:
            short_target = min(short_target, nearest_support)

        return {
            'long_entry': self.current_price,
            'long_stop_loss': long_stop_loss,
            'long_profit_target': long_target,
            'short_entry': self.current_price,
            'short_stop_loss': short_stop_loss,
            'short_profit_target': short_target,
        }

    def get_comprehensive_trade_plan(self, final_recommendation: Dict, analysis_results: Dict) -> Dict[str, Any]:
        """خطة التداول الشاملة"""
        signal = final_recommendation.get('main_action', 'انتظار')
        trade_plan = {'signal': signal}

        if 'شراء' in signal:
            levels = self.get_trade_levels(analysis_results)
            position_info = self.calculate_position_size(levels['long_entry'], levels['long_stop_loss'])
            risk = abs(levels['long_entry'] - levels['long_stop_loss'])
            reward = abs(levels['long_profit_target'] - levels['long_entry'])
            trade_plan.update({
                'direction': 'Long', 'entry_price': levels['long_entry'],
                'stop_loss': levels['long_stop_loss'], 'profit_target': levels['long_profit_target'],
                'position_sizing': position_info, 'risk_reward_ratio': reward / risk if risk > 0 else 0
            })
        elif 'بيع' in signal:
            levels = self.get_trade_levels(analysis_results)
            position_info = self.calculate_position_size(levels['short_entry'], levels['short_stop_loss'])
            risk = abs(levels['short_entry'] - levels['short_stop_loss'])
            reward = abs(levels['short_profit_target'] - levels['short_entry'])
            trade_plan.update({
                'direction': 'Short', 'entry_price': levels['short_entry'],
                'stop_loss': levels['short_stop_loss'], 'profit_target': levels['short_profit_target'],
                'position_sizing': position_info, 'risk_reward_ratio': reward / risk if risk > 0 else 0
            })
        else: # "انتظار"
            patterns = analysis_results.get('patterns', {}).get('found_patterns', [])
            if patterns and 'قيد التكوين' in patterns[0].get('status', ''):
                p = patterns[0]
                p_name = p.get('name', '')
                entry = p.get('resistance_line', p.get('neckline', 0))
                sl = p.get('support_line', p.get('support_line_start', 0))
                if sl == 0 and 'قاع مزدوج' in p_name: sl = (p.get('bottom_1_price', 0) + p.get('bottom_2_price', 0)) / 2
                if sl == 0 and 'قمة مزدوجة' in p_name: sl = p.get('neckline', 0)

                target = p.get('calculated_target', 0)

                is_bullish = 'صاعد' in p_name or 'قاع' in p_name

                if is_bullish and entry > 0 and sl > 0 and target > 0:
                    stop_price = sl * 0.998
                    risk = abs(entry - stop_price)
                    reward = abs(target - entry)
                    rr_ratio = reward / risk if risk > 0 else 0
                    trade_plan.update({
                        'trade_idea_name': f"مراقبة اختراق نمط {p_name}",
                        'conditional_entry': entry,
                        'conditional_stop_loss': stop_price,
                        'conditional_profit_target': target,
                        'risk_reward_ratio': rr_ratio
                    })
                elif not is_bullish and entry > 0 and sl > 0 and target > 0:
                    entry_price = sl
                    stop_price = entry * 1.002
                    risk = abs(entry_price - stop_price)
                    reward = abs(entry_price - target)
                    rr_ratio = reward / risk if risk > 0 else 0
                    trade_plan.update({
                        'trade_idea_name': f"مراقبة كسر نمط {p_name}",
                        'conditional_entry': entry_price,
                        'conditional_stop_loss': stop_price,
                        'conditional_profit_target': target,
                        'risk_reward_ratio': rr_ratio
                    })
                else:
                    trade_plan['recommendation'] = "لا توجد صفقة حالياً. مراقبة السوق."
            else:
                trade_plan['recommendation'] = "لا توجد صفقة حالياً. مراقبة السوق."

        return trade_plan
