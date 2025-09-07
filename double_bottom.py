import numpy as np
import pandas as pd
from typing import Dict, List
from sklearn.linear_model import LinearRegression
from scipy import stats

def calculate_dynamic_confidence(df: pd.DataFrame, config: dict, base_confidence: float = 70, is_bullish: bool = True) -> float:
    """حساب الثقة الديناميكية بناءً على عوامل السوق"""
    confidence = base_confidence
    
    # عامل الحجم
    if 'volume' in df.columns and len(df) > 20:
        recent_volume = df['volume'].tail(10).mean()
        avg_volume = df['volume'].mean()
        if recent_volume > avg_volume * 1.2:
            confidence += 10
        elif recent_volume < avg_volume * 0.8:
            confidence -= 5
    
    # عامل التقلبات
    volatility = df['close'].pct_change().tail(20).std()
    if 0.01 < volatility < 0.03:
        confidence += 5
    elif volatility > 0.05:
        confidence -= 10
    
    # عامل الاتجاه العام
    trend = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
    if is_bullish and trend > 0:
        confidence += 5
    elif not is_bullish and trend < 0:
        confidence += 5
    else:
        confidence -= 5
    
    return min(95, max(30, confidence))

def check_double_bottom(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict], 
                       current_price: float, price_tolerance: float) -> List[Dict]:
    """
    كاشف القاع المزدوج المتطور - يكشف أنماط W مثالية
    """
    patterns = []
    
    if len(lows) < 2 or len(highs) < 1:
        return patterns
    
    # البحث عن أزواج القيعان المتشابهة
    for i in range(len(lows) - 1):
        for j in range(i + 1, len(lows)):
            bottom1 = lows[i]
            bottom2 = lows[j]
            
            # التحقق من تشابه مستوى القيعان
            price_similarity = abs(bottom1['price'] - bottom2['price']) / min(bottom1['price'], bottom2['price'])
            
            if price_similarity > price_tolerance:
                continue
            
            # البحث عن القمة المتوسطة (خط العنق)
            intervening_highs = [h for h in highs if bottom1['index'] < h['index'] < bottom2['index']]
            
            if not intervening_highs:
                continue
            
            # اختيار أعلى قمة كخط عنق
            neckline_high = max(intervening_highs, key=lambda x: x['price'])
            neckline_price = neckline_high['price']
            
            # التأكد من أن القيعان أسفل خط العنق
            if bottom1['price'] >= neckline_price or bottom2['price'] >= neckline_price:
                continue
            
            # حساب عمق النمط
            avg_bottom_price = (bottom1['price'] + bottom2['price']) / 2
            pattern_depth = neckline_price - avg_bottom_price
            
            if pattern_depth <= 0:
                continue
            
            # التحقق من الحد الأدنى للعمق (1% من السعر)
            min_depth = avg_bottom_price * 0.01
            if pattern_depth < min_depth:
                continue
            
            # تحليل تماثل النمط
            time_between_bottoms = bottom2['index'] - bottom1['index']
            left_side_duration = neckline_high['index'] - bottom1['index']
            right_side_duration = bottom2['index'] - neckline_high['index']
            
            # تقييم التماثل الزمني
            symmetry_ratio = min(left_side_duration, right_side_duration) / max(left_side_duration, right_side_duration)
            
            # البحث عن قمم إضافية لتأكيد خط العنق
            neckline_highs = [neckline_high]
            
            # البحث عن قمم أخرى قريبة من مستوى خط العنق
            for h in highs:
                if h != neckline_high and abs(h['price'] - neckline_price) / neckline_price <= price_tolerance * 0.5:
                    neckline_highs.append(h)
            
            # تحديد حالة النمط
            breakout_occurred = current_price > neckline_price * (1 + price_tolerance * 0.5)
            false_breakdown = current_price < avg_bottom_price * (1 - price_tolerance)
            
            if false_breakdown:
                continue  # النمط فاشل
            
            status = 'مكتمل ✅' if breakout_occurred else 'قيد التكوين 🟡'
            
            # حساب الأهداف
            conservative_target = neckline_price + (pattern_depth * 0.8)
            aggressive_target = neckline_price + pattern_depth
            fibonacci_target = neckline_price + (pattern_depth * 1.618)
            
            # تحليل الحجم عند القيعان
            volume_analysis = {}
            if 'volume' in df.columns:
                bottom1_volume = df.iloc[bottom1['index']]['volume'] if bottom1['index'] < len(df) else 0
                bottom2_volume = df.iloc[bottom2['index']]['volume'] if bottom2['index'] < len(df) else 0
                neckline_volume = df.iloc[neckline_high['index']]['volume'] if neckline_high['index'] < len(df) else 0
                avg_volume = df['volume'].mean()
                
                volume_analysis = {
                    'bottom1_volume_strength': bottom1_volume / avg_volume if avg_volume > 0 else 1,
                    'bottom2_volume_strength': bottom2_volume / avg_volume if avg_volume > 0 else 1,
                    'neckline_volume_strength': neckline_volume / avg_volume if avg_volume > 0 else 1,
                    'volume_confirmation': bottom2_volume > bottom1_volume and neckline_volume > avg_volume * 1.2
                }
            
            # حساب الثقة المتقدمة
            base_confidence = 60
            
            # إضافات الثقة
            confidence_bonuses = 0
            confidence_bonuses += min(15, len(neckline_highs) * 5)  # المزيد من نقاط خط العنق
            confidence_bonuses += min(10, symmetry_ratio * 10)  # تماثل أفضل
            confidence_bonuses += min(10, (pattern_depth / avg_bottom_price) * 200)  # عمق أكبر
            
            # تحليل قوة القيعان
            bottom_strength = (bottom1.get('strength', 1) + bottom2.get('strength', 1)) / 2
            confidence_bonuses += min(15, bottom_strength * 3)
            
            # تحليل التسلسل الزمني المثالي
            if 10 <= time_between_bottoms <= 50:
                confidence_bonuses += 5
            elif time_between_bottoms > 100:
                confidence_bonuses -= 10
            
            # تحليل الحجم
            if volume_analysis and volume_analysis['volume_confirmation']:
                confidence_bonuses += 15
            elif volume_analysis and not volume_analysis['volume_confirmation']:
                confidence_bonuses -= 5
            
            final_confidence = calculate_dynamic_confidence(df, config, 
                                                          base_confidence + confidence_bonuses, 
                                                          is_bullish=True)
            
            # حساب مستويات إدارة المخاطر
            stop_loss = avg_bottom_price * 0.98
            risk_amount = abs(neckline_price - stop_loss)
            reward_amount = abs(conservative_target - neckline_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            
            # تقييم جودة النمط
            pattern_quality_score = (
                symmetry_ratio * 20 +
                len(neckline_highs) * 15 +
                min(30, (pattern_depth / avg_bottom_price) * 300) +
                min(20, bottom_strength * 5) +
                (15 if volume_analysis.get('volume_confirmation', False) else 0)
            )
            
            # تحليل موقع السعر في النمط
            price_position = "غير محدد"
            if current_price <= avg_bottom_price * 1.02:
                price_position = "قرب القيعان"
            elif current_price <= neckline_price * 0.98:
                price_position = "وسط النمط"
            elif current_price <= neckline_price * 1.02:
                price_position = "قرب خط العنق"
            else:
                price_position = "فوق خط العنق"
            
            patterns.append({
                'name': 'قاع مزدوج (Double Bottom)',
                'status': status,
                'confidence': round(final_confidence, 1),
                'pattern_strength': round(pattern_quality_score, 1),
                
                # خطوط النمط
                'neckline': round(neckline_price, 6),
                'bottom_1_price': round(bottom1['price'], 6),
                'bottom_2_price': round(bottom2['price'], 6),
                'average_bottom': round(avg_bottom_price, 6),
                
                # أهداف متعددة
                'conservative_target': round(conservative_target, 6),
                'aggressive_target': round(aggressive_target, 6),
                'fibonacci_target': round(fibonacci_target, 6),
                'calculated_target': round(conservative_target, 6),  # للتوافق
                
                # إدارة المخاطر
                'stop_loss': round(stop_loss, 6),
                'risk_reward_ratio': round(risk_reward_ratio, 2),
                
                # تفاصيل النمط
                'pattern_depth': round(pattern_depth, 6),
                'pattern_depth_percentage': round((pattern_depth / avg_bottom_price) * 100, 2),
                'neckline_touches': len(neckline_highs),
                'time_between_bottoms': time_between_bottoms,
                'symmetry_ratio': round(symmetry_ratio, 2),
                
                # تحليل الحجم
                'volume_analysis': volume_analysis,
                
                # معلومات إضافية
                'price_position': price_position,
                'pattern_maturity': round((time_between_bottoms / 50) * 100, 1),  # نسبة نضج النمط
                'entry_signal': 'كسر خط العنق' if not breakout_occurred else 'دخل بالفعل',
                'timeframe_suitability': 'ممتاز' if 15 <= time_between_bottoms <= 40 else 'جيد',
                
                # مؤشرات التأكيد
                'w_shape_quality': 'ممتاز' if symmetry_ratio > 0.8 else 'جيد' if symmetry_ratio > 0.6 else 'متوسط',
                'volume_confirmation_strength': 'قوي' if volume_analysis.get('volume_confirmation', False) else 'ضعيف'
            })
            
            break  # نكتفي بأفضل نمط
    
    return patterns
