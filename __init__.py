import os
import importlib
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.signal import find_peaks, argrelextrema
from sklearn.linear_model import LinearRegression
import warnings
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class AdvancedPatternDetector:
    """
    نظام كشف الأنماط المتقدم - يعمل على جميع الأطر الزمنية
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df.reset_index(drop=True, inplace=True)
        self.timeframe_factor = self._determine_timeframe_factor()
        
    def _determine_timeframe_factor(self) -> float:
        """تحديد عامل الإطار الزمني لتعديل حساسية الكشف"""
        if len(self.df) < 50:
            return 0.5  # إطار زمني قصير جداً (1-5 دقائق)
        elif len(self.df) < 200:
            return 0.7  # إطار زمني قصير (15-30 دقيقة)
        elif len(self.df) < 500:
            return 1.0  # إطار زمني متوسط (1-4 ساعات)
        else:
            return 1.5  # إطار زمني طويل (يومي وأعلى)
    
    def _adaptive_smoothing(self, prices: pd.Series, window: int = None) -> pd.Series:
        """تنعيم تكيفي بناءً على الإطار الزمني"""
        if window is None:
            base_window = max(3, int(len(prices) * 0.05))
            window = max(3, int(base_window * self.timeframe_factor))
        
        return prices.rolling(window=window, center=True).mean().fillna(prices)
    
    def _detect_pivot_points(self, order: int = None) -> Tuple[List[Dict], List[Dict]]:
        """كشف نقاط الانعطاف بدقة عالية"""
        if order is None:
            # تعديل الحساسية بناءً على الإطار الزمني
            base_order = max(2, int(len(self.df) * 0.02))
            order = max(2, int(base_order * self.timeframe_factor))
        
        # تنعيم البيانات لتقليل الضوضاء
        smoothed_high = self._adaptive_smoothing(self.df['high'])
        smoothed_low = self._adaptive_smoothing(self.df['low'])
        
        # كشف القمم والقيعان
        high_peaks, high_props = find_peaks(smoothed_high, distance=order, prominence=smoothed_high.std() * 0.5)
        low_peaks, low_props = find_peaks(-smoothed_low, distance=order, prominence=smoothed_low.std() * 0.5)
        
        # إنشاء قوائم القمم والقيعان
        highs = []
        for i, peak in enumerate(high_peaks):
            if peak < len(self.df):
                highs.append({
                    'index': peak,
                    'price': self.df.iloc[peak]['high'],
                    'volume': self.df.iloc[peak]['volume'] if 'volume' in self.df.columns else 0,
                    'strength': high_props['prominences'][i] if i < len(high_props['prominences']) else 1.0
                })
        
        lows = []
        for i, peak in enumerate(low_peaks):
            if peak < len(self.df):
                lows.append({
                    'index': peak,
                    'price': self.df.iloc[peak]['low'],
                    'volume': self.df.iloc[peak]['volume'] if 'volume' in self.df.columns else 0,
                    'strength': low_props['prominences'][i] if i < len(low_props['prominences']) else 1.0
                })
        
        # ترتيب حسب الفهرس
        highs.sort(key=lambda x: x['index'])
        lows.sort(key=lambda x: x['index'])
        
        return highs, lows
    
    def _calculate_pattern_strength(self, pattern_data: Dict, highs: List[Dict], lows: List[Dict]) -> float:
        """حساب قوة النمط بناءً على عوامل متعددة"""
        strength_score = 0.0
        
        # عامل الحجم
        if 'volume' in self.df.columns:
            avg_volume = self.df['volume'].mean()
            recent_volume = self.df['volume'].tail(10).mean()
            volume_factor = min(2.0, recent_volume / avg_volume) if avg_volume > 0 else 1.0
            strength_score += volume_factor * 20
        
        # عامل التقلبات
        volatility = self.df['close'].pct_change().std()
        if volatility > 0:
            volatility_factor = min(2.0, volatility * 100)
            strength_score += volatility_factor * 10
        
        # عامل عدد نقاط التلامس
        touch_points = len([h for h in highs if h.get('strength', 0) > 0]) + \
                      len([l for l in lows if l.get('strength', 0) > 0])
        strength_score += min(30, touch_points * 5)
        
        # عامل الاتجاه العام
        if len(self.df) > 1:
            trend_strength = abs(self.df['close'].iloc[-1] - self.df['close'].iloc[0]) / self.df['close'].iloc[0]
            strength_score += min(20, trend_strength * 100)
        
        return min(100, strength_score)
    
    def _get_dynamic_price_tolerance(self) -> float:
        """حساب تحمل السعر الديناميكي"""
        # حساب التقلبات الحديثة
        recent_volatility = self.df['close'].tail(20).pct_change().std()
        
        # تعديل التحمل بناءً على الإطار الزمني والتقلبات
        base_tolerance = 0.02  # 2% أساسي
        volatility_adjustment = recent_volatility * 2 if recent_volatility > 0 else 0
        timeframe_adjustment = 0.01 / self.timeframe_factor
        
        return min(0.05, base_tolerance + volatility_adjustment + timeframe_adjustment)
    
    def _enhance_pattern_data(self, pattern: Dict, highs: List[Dict] = None, lows: List[Dict] = None) -> Dict:
        """تعزيز بيانات النمط بمعلومات إضافية"""
        enhanced_pattern = pattern.copy()
        
        # ضمان وجود الحقول الأساسية
        if 'confidence' not in enhanced_pattern:
            enhanced_pattern['confidence'] = 60
        
        if highs is None:
            highs = []
        if lows is None:
            lows = []
        
        # إضافة قوة النمط
        enhanced_pattern['pattern_strength'] = self._calculate_pattern_strength(pattern, highs, lows)
        
        # إضافة مستوى المخاطرة
        if 'support_line' in pattern and 'resistance_line' in pattern and len(self.df) > 0:
            try:
                risk_reward_ratio = abs(pattern.get('calculated_target', 0) - self.df['close'].iloc[-1]) / \
                                  abs(pattern['resistance_line'] - pattern['support_line'])
                enhanced_pattern['risk_reward_ratio'] = round(risk_reward_ratio, 2)
            except (ZeroDivisionError, KeyError):
                enhanced_pattern['risk_reward_ratio'] = 0.0
        
        # إضافة توقيت مقترح للدخول
        enhanced_pattern['entry_timing'] = self._suggest_entry_timing(pattern)
        
        # إضافة مستوى التأكيد
        enhanced_pattern['confirmation_level'] = self._calculate_confirmation_level(pattern)
        
        # إضافة الإطار الزمني المناسب
        enhanced_pattern['recommended_timeframe'] = self._get_timeframe_recommendation()
        
        return enhanced_pattern
    
    def _suggest_entry_timing(self, pattern: Dict) -> str:
        """اقتراح توقيت الدخول"""
        if len(self.df) == 0:
            return 'انتظار تأكيد إضافي'
            
        current_price = self.df['close'].iloc[-1]
        
        if pattern.get('status') == 'مكتمل ✅':
            return 'دخول فوري'
        elif 'resistance_line' in pattern and 'support_line' in pattern:
            resistance = pattern['resistance_line']
            support = pattern['support_line']
            
            if abs(current_price - resistance) < abs(current_price - support):
                return 'انتظار كسر المقاومة'
            else:
                return 'انتظار اختبار الدعم'
        else:
            return 'انتظار تأكيد إضافي'
    
    def _calculate_confirmation_level(self, pattern: Dict) -> str:
        """حساب مستوى التأكيد"""
        confidence = pattern.get('confidence', 0)
        strength = pattern.get('pattern_strength', 0)
        
        combined_score = (confidence + strength) / 2
        
        if combined_score >= 80:
            return 'تأكيد عالي جداً'
        elif combined_score >= 70:
            return 'تأكيد عالي'
        elif combined_score >= 60:
            return 'تأكيد متوسط'
        else:
            return 'تأكيد ضعيف'
    
    def _get_timeframe_recommendation(self) -> str:
        """توصية الإطار الزمني المناسب"""
        if self.timeframe_factor <= 0.5:
            return 'قصير المدى (1-15 دقيقة)'
        elif self.timeframe_factor <= 1.0:
            return 'متوسط المدى (30 دقيقة - 4 ساعات)'
        else:
            return 'طويل المدى (يومي وأعلى)'

def check_all_patterns(df: pd.DataFrame, config: dict = None, 
                      highs: List[Dict] = None, lows: List[Dict] = None, 
                      current_price: float = None, price_tolerance: float = None) -> List[Dict]:
    """
    نظام كشف الأنماط المتطور - يدعم التحميل الديناميكي والكشف المتقدم
    """
    if config is None:
        config = {}
    
    if df is None or len(df) == 0:
        return []
    
    # إنشاء كاشف الأنماط المتقدم
    detector = AdvancedPatternDetector(df)
    
    # كشف نقاط الانعطاف تلقائياً إذا لم تُمرر
    if highs is None or lows is None:
        highs, lows = detector._detect_pivot_points()
    
    # تحديد السعر الحالي وتحمل السعر تلقائياً
    if current_price is None:
        current_price = df['close'].iloc[-1]
    
    if price_tolerance is None:
        price_tolerance = detector._get_dynamic_price_tolerance()
    
    all_patterns = []
    
    # محاولة التحميل الديناميكي للأنماط
    try:
        current_dir = os.path.dirname(__file__)
        
        if os.path.exists(current_dir):
            for filename in os.listdir(current_dir):
                if (filename.endswith('.py') and 
                    not filename.startswith('__') and 
                    'utils' not in filename and
                    filename != 'pattern_main.py'):
                    
                    module_name = filename[:-3]
                    try:
                        module = importlib.import_module(f".{module_name}", package='analysis.patterns')
                        
                        # البحث عن دالة تبدأ بـ 'check_'
                        checker_function_name = next((f for f in dir(module) if f.startswith('check_')), None)
                        
                        if checker_function_name:
                            checker_function = getattr(module, checker_function_name)
                            found = checker_function(df, config, highs, lows, current_price, price_tolerance)
                            if found:
                                all_patterns.extend(found)
                                logger.info(f"Pattern checker '{checker_function_name}' found {len(found)} pattern(s).")
                    except Exception as e:
                        logger.error(f"Error processing pattern module {module_name}: {e}")
                        continue
        
    except Exception as e:
        logger.warning(f"Dynamic loading failed, using static imports: {e}")
        
        # في حالة فشل التحميل الديناميكي، استخدم الاستيراد الثابت
        try:
            from .ascending_triangle import check_ascending_triangle
            from .double_bottom import check_double_bottom
            from .bull_flag import check_bull_flag
            from .bear_flag import check_bear_flag
            from .falling_wedge import check_falling_wedge
            from .rising_wedge import check_rising_wedge
            
            pattern_checkers = [
                check_ascending_triangle,
                check_double_bottom,
                check_bull_flag,
                check_bear_flag,
                check_falling_wedge,
                check_rising_wedge
            ]
            
            for checker in pattern_checkers:
                try:
                    found = checker(df, config, highs, lows, current_price, price_tolerance)
                    if found:
                        all_patterns.extend(found)
                except Exception as e:
                    logger.error(f"Error in pattern checker {checker.__name__}: {e}")
                    continue
                    
        except ImportError as e:
            logger.error(f"Static imports also failed: {e}")
    
    # تعزيز بيانات الأنماط المكتشفة
    enhanced_patterns = []
    for pattern in all_patterns:
        try:
            enhanced_pattern = detector._enhance_pattern_data(pattern, highs, lows)
            enhanced_patterns.append(enhanced_pattern)
        except Exception as e:
            logger.error(f"Error enhancing pattern: {e}")
            # إضافة النمط بدون تعزيز
            enhanced_patterns.append(pattern)
    
    # ترتيب الأنماط حسب القوة والثقة
    try:
        enhanced_patterns.sort(
            key=lambda x: (x.get('pattern_strength', 0) + x.get('confidence', 0)), 
            reverse=True
        )
    except Exception as e:
        logger.error(f"Error sorting patterns: {e}")
    
    return enhanced_patterns
