def calculate_dynamic_confidence(df, config, base_confidence=70, is_bullish=True):
    """
    حساب الثقة الديناميكية للنماذج بناءً على قوة الإشارة والحجم والتقلبات

    Args:
        df: DataFrame يحتوي على بيانات السعر والحجم
        config: إعدادات التحليل
        base_confidence: الثقة الأساسية (افتراضي 70)
        is_bullish: هل النموذج صاعد أم هابط

    Returns:
        float: قيمة الثقة المحسوبة بين 30 و 95
    """
    try:
        # تحليل الحجم
        if 'volume' in df.columns:
            recent_volume = df['volume'].tail(10).mean()
            avg_volume = df['volume'].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        else:
            volume_ratio = 1

        # تحليل التقلبات
        if len(df) > 1:
            volatility = df['close'].pct_change().std()
        else:
            volatility = 0

        # حساب تعديل الحجم (بين -20 و +20)
        volume_adjustment = min(20, max(-20, (volume_ratio - 1) * 30))

        # حساب تعديل التقلبات (بين -15 و +15)
        volatility_adjustment = min(15, max(-15, (0.02 - volatility) * 100))

        # الثقة النهائية
        final_confidence = base_confidence + volume_adjustment + volatility_adjustment

        # ضمان أن النتيجة بين 30 و 95
        return max(30, min(95, final_confidence))

    except Exception as e:
        # في حالة حدوث خطأ، إرجاع الثقة الأساسية
        return base_confidence

# إنشاء alias للتوافق مع الكود الحالي
_calculate_dynamic_confidence = calculate_dynamic_confidence
