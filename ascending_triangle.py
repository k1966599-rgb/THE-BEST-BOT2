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
    if 0.01 < volatility < 0.03:  # تقلبات مثالية
        confidence += 5
    elif volatility > 0.05:  # تقلبات عالية
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

def check_ascending_triangle(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict], 
                           current_price: float, price_tolerance: float) -> List[Dict]:
    """
    كاشف المثلث الصاعد المتطور - يعمل على جميع الأطر الزمنية
    """
    patterns = []
    
    if len(highs) < 3 or len(lows) < 3:
        return patterns
    
    # تحسين اكتشاف خط المقاومة الأفقي
    resistance_candidates = []
    
    # البحث عن مجموعات من القمم المتقاربة
    for i in range(len(highs) - 1):
        similar_highs = [highs[i]]
        base_price = highs[i]['price']
        
        for j in range(i + 1, len(highs)):
            price_diff = abs(highs[j]['price'] - base_price) / base_price
            if price_diff <= price_tolerance:
                similar_highs.append(highs[j])
        
        if len(similar_highs) >= 2:
            # حساب قوة خط المقاومة
            resistance_strength = sum([h.get('strength', 1) for h in similar_highs])
            resistance_price = np.mean([h['price'] for h in similar_highs])
            
            resistance_candidates.append({
                'price': resistance_price,
                'touches': len(similar_highs),
                'strength': resistance_strength,
                'points': similar_highs
            })
    
    # اختيار أفضل خط مقاومة
    if not resistance_candidates:
        return patterns
    
    best_resistance = max(resistance_candidates, key=lambda x: x['touches'] * x['strength'])
    resistance_line_price = best_resistance['price']
    resistance_touches = best_resistance['touches']
    
    # البحث عن سلسلة من القيعان المرتفعة
    valid_lows = [low for low in lows if low['price'] < resistance_line_price * 0.95]
    
    if len(valid_lows) < 2:
        return patterns
    
    # فحص اتجاه القيعان الصاعد
    ascending_lows = []
    trend_violations = 0
    
    for i in range(len(valid_lows)):
        if i == 0:
            ascending_lows.append(valid_lows[i])
        else:
            if valid_lows[i]['price'] > valid_lows[i-1]['price']:
                ascending_lows.append(valid_lows[i])
            else:
                trend_violations += 1
                if trend_violations <= 1:  # السماح بانتهاك واحد
                    ascending_lows.append(valid_lows[i])
    
    if len(ascending_lows) < 2:
        return patterns
    
    # حساب خط الدعم الصاعد باستخدام الانحدار الخطي
    x_values = np.array([low['index'] for low in ascending_lows]).reshape(-1, 1)
    y_values = np.array([low['price'] for low in ascending_lows])
    
    reg = LinearRegression().fit(x_values, y_values)
    support_slope = reg.coef_[0]
    r_squared = reg.score(x_values, y_values)
    
    # التأكد من أن خط الدعم صاعد بشكل كافي
    if support_slope <= 0 or r_squared < 0.6:
        return patterns
    
    # حساب السعر الحالي لخط الدعم
    current_support_price = reg.predict([[len(df) - 1]])[0]
    
    # التأكد من التقارب (المثلث يجب أن يضيق)
    triangle_width_start = resistance_line_price - ascending_lows[0]['price']
    triangle_width_current = resistance_line_price - current_support_price
    
    if triangle_width_current >= triangle_width_start:
        return patterns
    
    # حساب نقطة التقاطع المتوقعة
    convergence_point = (resistance_line_price - reg.intercept_) / support_slope
    
    # التأكد من أن النمط لم يصل لنقطة التقاطع بعد
    if len(df) >= convergence_point:
        return patterns
    
    # تحديد حالة النمط
    breakout_occurred = current_price > resistance_line_price * (1 + price_tolerance * 0.5)
    breakdown_occurred = current_price < current_support_price * (1 - price_tolerance * 0.5)
    
    if breakdown_occurred:
        return patterns  # النمط فاشل
    
    status = 'مكتمل ✅' if breakout_occurred else 'قيد التكوين 🟡'
    
    # حساب الهدف المحسن
    triangle_height = resistance_line_price - ascending_lows[0]['price']
    conservative_target = resistance_line_price + (triangle_height * 0.8)
    aggressive_target = resistance_line_price + triangle_height
    
    # حساب الثقة المتقدمة
    base_confidence = 65
    
    # إضافات الثقة
    confidence_bonuses = 0
    confidence_bonuses += min(15, resistance_touches * 3)  # المزيد من اللمسات = ثقة أكبر
    confidence_bonuses += min(10, len(ascending_lows) * 2)  # المزيد من القيعان الصاعدة
    confidence_bonuses += min(10, r_squared * 10)  # قوة الاتجاه الخطي
    
    # حساب عامل الحجم
    if 'volume' in df.columns:
        resistance_volume = np.mean([df.iloc[point['index']]['volume'] 
                                   for point in best_resistance['points'] 
                                   if point['index'] < len(df)])
        avg_volume = df['volume'].mean()
        
        if resistance_volume > avg_volume * 1.5:
            confidence_bonuses += 10
        elif resistance_volume < avg_volume * 0.7:
            confidence_bonuses -= 5
    
    # حساب عامل التوقيت
    pattern_duration = len(df) - ascending_lows[0]['index']
    if 10 <= pattern_duration <= 50:  # مدة مثالية
        confidence_bonuses += 5
    elif pattern_duration > 100:  # نمط قديم جداً
        confidence_bonuses -= 10
    
    final_confidence = calculate_dynamic_confidence(df, config, 
                                                  base_confidence + confidence_bonuses, 
                                                  is_bullish=True)
    
    # حساب مستويات إضافية
    stop_loss = current_support_price * 0.98
    risk_amount = abs(resistance_line_price - stop_loss)
    reward_amount = abs(conservative_target - resistance_line_price)
    risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
    
    # تقييم قوة النمط
    pattern_strength = min(100, (
        resistance_touches * 15 +
        len(ascending_lows) * 10 +
        r_squared * 30 +
        (1 - (triangle_width_current / triangle_width_start)) * 20 +
        min(20, risk_reward_ratio * 10)
    ))
    
    patterns.append({
        'name': 'مثلث صاعد (Ascending Triangle)',
        'status': status,
        'confidence': round(final_confidence, 1),
        'pattern_strength': round(pattern_strength, 1),
        
        # خطوط النمط
        'resistance_line': round(resistance_line_price, 6),
        'support_line_current': round(current_support_price, 6),
        'support_slope': round(support_slope, 8),
        
        # أهداف متعددة
        'conservative_target': round(conservative_target, 6),
        'aggressive_target': round(aggressive_target, 6),
        'calculated_target': round(conservative_target, 6),  # للتوافق مع النظام القديم
        
        # إدارة المخاطر
        'stop_loss': round(stop_loss, 6),
        'risk_reward_ratio': round(risk_reward_ratio, 2),
        
        # تفاصيل النمط
        'resistance_touches': resistance_touches,
        'ascending_lows_count': len(ascending_lows),
        'pattern_duration': pattern_duration,
        'triangle_compression': round((1 - triangle_width_current / triangle_width_start) * 100, 1),
        'convergence_point_distance': round(convergence_point - len(df), 1),
        
        # إشارات التداول
        'entry_signal': 'كسر المقاومة' if not breakout_occurred else 'دخل بالفعل',
        'volume_confirmation': resistance_volume > avg_volume * 1.2 if 'volume' in df.columns else False,
        
        # معلومات إضافية
        'timeframe_suitability': 'ممتاز' if 20 <= pattern_duration <= 60 else 'جيد',
        'trend_quality': 'قوي' if r_squared > 0.8 else 'متوسط' if r_squared > 0.6 else 'ضعيف'
    })
    
    return patterns
