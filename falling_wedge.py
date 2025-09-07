import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from sklearn.linear_model import LinearRegression

def find_trend_line(x_values: List[int], y_values: List[float]) -> Dict:
    """إيجاد خط الاتجاه باستخدام الانحدار الخطي"""
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

def check_falling_wedge(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict], 
                       current_price: float, price_tolerance: float) -> List[Dict]:
    """
    كاشف الوتد الهابط المتطور - نمط انعكاس صاعد
    """
    found_patterns = []
    
    if len(highs) < 3 or len(lows) < 3:
        return found_patterns
    
    # تحديد نافذة البحث بناءً على حجم البيانات
    search_window = min(80, len(df) // 2)
    search_data = df.tail(search_window)
    
    # تصفية النقاط ضمن نافذة البحث
    window_highs = [h for h in highs if h['index'] >= search_data.index[0]]
    window_lows = [l for l in lows if l['index'] >= search_data.index[0]]
    
    if len(window_highs) < 3 or len(window_lows) < 3:
        return found_patterns
    
    # فحص الوتد الهابط
    upper_trend = find_trend_line([p['index'] for p in window_highs], [p['price'] for p in window_highs])
    lower_trend = find_trend_line([p['index'] for p in window_lows], [p['price'] for p in window_lows])
    
    # شروط الوتد الهابط:
    # 1. كلا الخطين هابطين
    if upper_trend['slope'] >= 0 or lower_trend['slope'] >= 0:
        return found_patterns
    
    # 2. خط المقاومة أكثر انحداراً من خط الدعم (التقارب)
    if upper_trend['slope'] >= lower_trend['slope']:
        return found_patterns
    
    # 3. جودة الخطوط (R²)
    if upper_trend['r_squared'] < 0.6 or lower_trend['r_squared'] < 0.6:
        return found_patterns
    
    # حساب المستويات الحالية
    current_index = len(df) - 1
    resistance_current = upper_trend['slope'] * current_index + upper_trend['intercept']
    support_current = lower_trend['slope'] * current_index + lower_trend['intercept']
    
    # التأكد من أن السعر لا يزال ضمن الوتد
    if current_price < support_current * (1 - price_tolerance):
        return found_patterns  # كسر هابط = النمط فاشل
    
    # حساب نقطة التقارب
    if abs(upper_trend['slope'] - lower_trend['slope']) < 1e-10:
        return found_patterns  # الخطوط متوازية
    
    convergence_x = (lower_trend['intercept'] - upper_trend['intercept']) / (upper_trend['slope'] - lower_trend['slope'])
    
    # التأكد من أن التقارب في المستقبل
    if convergence_x <= current_index:
        return found_patterns
    
    # تحديد حالة النمط
    breakout_occurred = current_price > resistance_current * (1 + price_tolerance * 0.5)
    status = "مكتمل ✅" if breakout_occurred else "قيد التكوين 🟡"
    
    # حساب عرض الوتد في البداية والآن
    wedge_start_index = min([p['index'] for p in window_highs + window_lows])
    resistance_start = upper_trend['slope'] * wedge_start_index + upper_trend['intercept']
    support_start = lower_trend['slope'] * wedge_start_index + lower_trend['intercept']
    
    initial_width = resistance_start - support_start
    current_width = resistance_current - support_current
    compression_ratio = 1 - (current_width / initial_width) if initial_width > 0 else 0
    
    # تحليل الحجم
    volume_analysis = {}
    if 'volume' in df.columns:
        # حجم في بداية الوتد
        early_indices = [p['index'] for p in window_highs + window_lows if p['index'] <= wedge_start_index + 10]
        early_volume = np.mean([df.iloc[i]['volume'] for i in early_indices if i < len(df)]) if early_indices else 0
        
        # حجم في نهاية الوتد
        late_indices = [p['index'] for p in window_highs + window_lows if p['index'] >= current_index - 10]
        late_volume = np.mean([df.iloc[i]['volume'] for i in late_indices if i < len(df)]) if late_indices else 0
        
        # الحجم العام
        avg_volume = df['volume'].mean()
        
        volume_analysis = {
            'early_volume_strength': early_volume / avg_volume if avg_volume > 0 else 1,
            'late_volume_strength': late_volume / avg_volume if avg_volume > 0 else 1,
            'volume_decline': early_volume > late_volume * 1.2 if early_volume > 0 and late_volume > 0 else False,
            'breakout_volume': df.iloc[-1]['volume'] / avg_volume if avg_volume > 0 else 1
        }
    
    # حساب الثقة
    base_confidence = 65
    confidence_bonuses = 0
    
    # جودة الخطوط
    confidence_bonuses += min(20, (upper_trend['r_squared'] + lower_trend['r_squared']) * 10)
    
    # نسبة الضغط
    confidence_bonuses += min(15, compression_ratio * 30)
    
    # عدد نقاط التلامس
    confidence_bonuses += min(15, (len(window_highs) + len(window_lows)) * 1.5)
    
    # قوة التقارب
    convergence_strength = abs(upper_trend['slope'] - lower_trend['slope']) / abs(lower_trend['slope'])
    confidence_bonuses += min(10, convergence_strength * 20)
    
    # تأكيد الحجم
    if volume_analysis and volume_analysis['volume_decline']:
        confidence_bonuses += 10
    
    # المسافة من نقطة التقارب
    distance_to_convergence = convergence_x - current_index
    if 5 <= distance_to_convergence <= 30:
        confidence_bonuses += 10
    elif distance_to_convergence > 50:
        confidence_bonuses -= 5
    
    final_confidence = min(95, base_confidence + confidence_bonuses)
    
    # حساب الأهداف
    wedge_height = max([p['price'] for p in window_highs]) - min([p['price'] for p in window_lows])
    
    conservative_target = resistance_current + (wedge_height * 0.6)
    aggressive_target = resistance_current + wedge_height
    fibonacci_target = resistance_current + (wedge_height * 1.618)
    
    # إدارة المخاطر
    stop_loss = support_current * 0.98
    risk_amount = abs(resistance_current - stop_loss)
    reward_amount = abs(conservative_target - resistance_current)
    risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
    
    # تقييم قوة النمط
    pattern_strength = min(100, (
        (upper_trend['r_squared'] + lower_trend['r_squared']) * 25 +
        compression_ratio * 30 +
        len(window_highs + window_lows) * 2 +
        convergence_strength * 15 +
        (10 if volume_analysis.get('volume_decline', False) else 0)
    ))
    
    # مدة النمط
    pattern_duration = current_index - wedge_start_index
    
    pattern_info = {
        "name": "وتد هابط (Falling Wedge)",
        "status": status,
        "confidence": round(final_confidence, 1),
        "pattern_strength": round(pattern_strength, 1),
        
        # خطوط النمط
        "resistance_line": round(resistance_current, 6),
        "support_line": round(support_current, 6),
        "upper_slope": round(upper_trend['slope'], 8),
        "lower_slope": round(lower_trend['slope'], 8),
        
        # أهداف متعددة
        "conservative_target": round(conservative_target, 6),
        "aggressive_target": round(aggressive_target, 6),
        "fibonacci_target": round(fibonacci_target, 6),
        "calculated_target": round(conservative_target, 6),
        
        # إدارة المخاطر
        "stop_loss": round(stop_loss, 6),
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        
        # تفاصيل النمط
        "wedge_height": round(wedge_height, 6),
        "initial_width": round(initial_width, 6),
        "current_width": round(current_width, 6),
        "compression_ratio": round(compression_ratio * 100, 1),
        "convergence_distance": round(distance_to_convergence, 1),
        "pattern_duration": pattern_duration,
        
        # جودة الخطوط
        "upper_trendline_quality": round(upper_trend['r_squared'], 3),
        "lower_trendline_quality": round(lower_trend['r_squared'], 3),
        "convergence_strength": round(convergence_strength, 3),
        
        # تحليل الحجم
        "volume_analysis": volume_analysis,
        
        # معلومات إضافية
        "entry_signal": 'كسر المقاومة' if not breakout_occurred else 'دخل بالفعل',
        "timeframe_suitability": 'ممتاز' if 20 <= pattern_duration <= 70 else 'جيد',
        "wedge_maturity": round((compression_ratio * 100), 1),
        "breakout_proximity": 'قريب' if distance_to_convergence <= 15 else 'متوسط' if distance_to_convergence <= 30 else 'بعيد',
        "time_identified": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    found_patterns.append(pattern_info)
    return found_patterns
