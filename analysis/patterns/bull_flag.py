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

def check_bull_flag(df: pd.DataFrame, config: dict, highs: List[Dict], lows: List[Dict], 
                   current_price: float, price_tolerance: float) -> List[Dict]:
    """
    كاشف العلم الصاعد المتطور - يكشف أنماط الاستمرار الصاعدة
    """
    found_patterns = []
    
    if len(highs) < 3 or len(lows) < 3:
        return found_patterns
    
    # البحث عن أفضل سارية علم (flagpole)
    for i in range(len(lows) - 2, max(-1, len(lows) - 10), -1):
        flagpole_start_low = lows[i]
        
        # البحث عن قمة السارية
        potential_poles = [h for h in highs if h['index'] > flagpole_start_low['index']]
        if not potential_poles:
            continue
            
        flagpole_end_high = max(potential_poles, key=lambda x: x['price'])
        flagpole_height = flagpole_end_high['price'] - flagpole_start_low['price']
        flagpole_duration = flagpole_end_high['index'] - flagpole_start_low['index']
        
        # التحقق من قوة السارية
        min_flagpole_height = df['close'].mean() * 0.03  # 3% كحد أدنى
        if flagpole_height < min_flagpole_height:
            continue
        
        # التحقق من سرعة السارية (يجب أن تكون سريعة)
        flagpole_speed = flagpole_height / flagpole_duration if flagpole_duration > 0 else 0
        min_speed = df['close'].mean() * 0.001  # حد أدنى للسرعة
        
        if flagpole_speed < min_speed:
            continue
        
        # --- تحليل العلم ---
        flag_highs = [h for h in highs if h['index'] > flagpole_end_high['index']]
        flag_lows = [l for l in lows if l['index'] > flagpole_end_high['index']]
        
        if len(flag_highs) < 2 or len(flag_lows) < 2:
            continue
        
        # التحقق من عمق التصحيح
        deepest_retracement = min(flag_lows, key=lambda x: x['price'])
        retracement_level = (flagpole_end_high['price'] - deepest_retracement['price']) / flagpole_height
        
        # يجب ألا يتجاوز التصحيح 61.8%
        if retracement_level > 0.618:
            continue
        
        # تحليل اتجاه العلم
        upper_trend = find_trend_line([p['index'] for p in flag_highs], [p['price'] for p in flag_highs])
        lower_trend = find_trend_line([p['index'] for p in flag_lows], [p['price'] for p in flag_lows])
        
        # يجب أن يكون العلم منحدراً أو أفقياً
        if upper_trend['slope'] > flagpole_speed * 0.1 or lower_trend['slope'] > flagpole_speed * 0.1:
            continue
        
        # التحقق من التوازي
        slope_difference = abs(upper_trend['slope'] - lower_trend['slope'])
        max_slope_diff = abs(lower_trend['slope'] * 0.5) if lower_trend['slope'] != 0 else 0.001
        
        if slope_difference > max_slope_diff:
            continue
        
        # حساب مستويات العلم الحالية
        current_index = len(df) - 1
        resistance_current = upper_trend['slope'] * current_index + upper_trend['intercept']
        support_current = lower_trend['slope'] * current_index + lower_trend['intercept']
        
        # تحديد حالة النمط
        breakout_occurred = current_price > resistance_current * (1 + price_tolerance * 0.5)
        breakdown_occurred = current_price < support_current * (1 - price_tolerance * 0.5)
        
        if breakdown_occurred:
            continue  # النمط فاشل
        
        status = "مكتمل ✅" if breakout_occurred else "قيد التكوين 🟡"
        
        # تحليل الحجم
        volume_analysis = {}
        if 'volume' in df.columns:
            # حجم السارية
            flagpole_indices = range(flagpole_start_low['index'], flagpole_end_high['index'] + 1)
            flagpole_avg_volume = np.mean([df.iloc[i]['volume'] for i in flagpole_indices if i < len(df)])
            
            # حجم العلم
            flag_indices = [p['index'] for p in flag_highs + flag_lows if p['index'] < len(df)]
            flag_avg_volume = np.mean([df.iloc[i]['volume'] for i in flag_indices]) if flag_indices else 0
            
            # الحجم العام
            overall_avg_volume = df['volume'].mean()
            
            volume_analysis = {
                'flagpole_volume_strength': flagpole_avg_volume / overall_avg_volume if overall_avg_volume > 0 else 1,
                'flag_volume_strength': flag_avg_volume / overall_avg_volume if overall_avg_volume > 0 else 1,
                'volume_confirmation': (flagpole_avg_volume > overall_avg_volume * 1.3 and 
                                      flag_avg_volume < flagpole_avg_volume * 0.8),
                'breakout_volume': df.iloc[-1]['volume'] / overall_avg_volume if overall_avg_volume > 0 else 1
            }
        
        # حساب الثقة
        base_confidence = 70
        confidence_bonuses = 0
        
        # قوة السارية
        confidence_bonuses += min(15, (flagpole_height / df['close'].mean()) * 200)
        
        # جودة التصحيح
        if retracement_level < 0.382:
            confidence_bonuses += 10
        elif retracement_level < 0.5:
            confidence_bonuses += 5
        
        # جودة خطوط العلم
        confidence_bonuses += min(10, (upper_trend['r_squared'] + lower_trend['r_squared']) * 5)
        
        # عدد نقاط التلامس
        confidence_bonuses += min(10, (len(flag_highs) + len(flag_lows) - 4) * 2)
        
        # تأكيد الحجم
        if volume_analysis and volume_analysis['volume_confirmation']:
            confidence_bonuses += 15
        
        # مدة العلم المناسبة
        flag_duration = flag_highs[-1]['index'] - flagpole_end_high['index'] if flag_highs else 0
        if flagpole_duration * 0.5 <= flag_duration <= flagpole_duration * 2:
            confidence_bonuses += 5
        
        final_confidence = min(95, base_confidence + confidence_bonuses)
        
        # حساب الأهداف
        conservative_target = resistance_current + (flagpole_height * 0.8)
        aggressive_target = resistance_current + flagpole_height
        fibonacci_target = resistance_current + (flagpole_height * 1.618)
        
        # إدارة المخاطر
        stop_loss = support_current * 0.98
        risk_amount = abs(resistance_current - stop_loss)
        reward_amount = abs(conservative_target - resistance_current)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        # تقييم قوة النمط
        pattern_strength = min(100, (
            (flagpole_height / df['close'].mean()) * 300 +
            (1 - retracement_level) * 30 +
            (upper_trend['r_squared'] + lower_trend['r_squared']) * 25 +
            len(flag_highs + flag_lows) * 3 +
            (15 if volume_analysis.get('volume_confirmation', False) else 0)
        ))
        
        # تحليل التوقيت
        total_pattern_duration = (flag_highs[-1]['index'] if flag_highs else current_index) - flagpole_start_low['index']
        pattern_maturity = min(100, (total_pattern_duration / 50) * 100)
        
        pattern_info = {
            "name": "علم صاعد (Bull Flag)",
            "status": status,
            "confidence": round(final_confidence, 1),
            "pattern_strength": round(pattern_strength, 1),
            
            # خطوط النمط
            "resistance_line": round(resistance_current, 6),
            "support_line": round(support_current, 6),
            "flagpole_start": round(flagpole_start_low['price'], 6),
            "flagpole_end": round(flagpole_end_high['price'], 6),
            
            # أهداف متعددة
            "conservative_target": round(conservative_target, 6),
            "aggressive_target": round(aggressive_target, 6),
            "fibonacci_target": round(fibonacci_target, 6),
            "calculated_target": round(conservative_target, 6),
            
            # إدارة المخاطر
            "stop_loss": round(stop_loss, 6),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            
            # تفاصيل النمط
            "flagpole_height": round(flagpole_height, 6),
            "flagpole_height_percentage": round((flagpole_height / flagpole_start_low['price']) * 100, 2),
            "retracement_level": round(retracement_level * 100, 1),
            "flagpole_duration": flagpole_duration,
            "flag_duration": flag_duration,
            "flagpole_speed": round(flagpole_speed, 8),
            
            # تحليل الحجم
            "volume_analysis": volume_analysis,
            
            # جودة النمط
            "upper_trendline_quality": round(upper_trend['r_squared'], 2),
            "lower_trendline_quality": round(lower_trend['r_squared'], 2),
            "flag_slope_upper": round(upper_trend['slope'], 8),
            "flag_slope_lower": round(lower_trend['slope'], 8),
            
            # معلومات إضافية
            "pattern_maturity": round(pattern_maturity, 1),
            "entry_signal": 'كسر مقاومة العلم' if not breakout_occurred else 'دخل بالفعل',
            "timeframe_suitability": 'ممتاز' if 10 <= total_pattern_duration <= 60 else 'جيد',
            "retracement_quality": ('ممتاز' if retracement_level < 0.382 else 
                                  'جيد' if retracement_level < 0.5 else 'مقبول'),
            "time_identified": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        found_patterns.append(pattern_info)
        break  # نكتفي بأحدث نمط
    
    return found_patterns
