# -*- coding: utf-8 -*-

TEXTS = {
    'ar': {
        # --- Main Report Structure ---
        "report_title": "📊 **التحليل الاستراتيجي الشامل لـ {symbol} | إطار {timeframe}**",
        "report_updated_at": "*بتاريخ: {date} | الساعة: {time}*",
        "disclaimer": "*تحليل آلي، ليس توصية استثمارية مباشرة.*",

        # --- Section 1: Executive Summary ---
        "section_summary_title": "--- 1. الخلاصة التنفيذية ---",
        "summary_signal": "الإشارة الحالية",
        "summary_conclusion": "الخلاصة",
        "summary_key_level": "أهم مستوى للمراقبة",

        # --- Section 2: Trade/Monitoring Plan ---
        "section_trade_plan_title": "--- 2. خطة التداول المقترحة ---",
        "trade_logic": "منطق الصفقة",
        "trade_risk_assessment": "تقييم المخاطر",
        "risk_to_reward": "المخاطرة/العائد (للهدف الأول)",
        "confidence": "مستوى الثقة",
        "entry_zone": "منطقة الدخول",
        "best_entry": "أفضل سعر للدخول",
        "stop_loss": "وقف الخسارة (SL)",
        "targets": "الأهداف (TP)",

        "section_monitoring_plan_title": "--- 2. خطة المراقبة ---",
        "monitoring_conclusion": "الوضع الحالي",
        "monitoring_bullish_scenario": "السيناريو الصاعد (للمراقبة)",
        "monitoring_bearish_scenario": "السيناريو الهابط (للمراقبة)",
        "monitoring_activation_condition": "شرط التفعيل",
        "monitoring_expected_targets": "الأهداف المتوقعة",

        # --- Section 3: Technical Analysis Details ---
        "section_analysis_details_title": "--- 3. تفاصيل التحليل الفني ---",
        "details_market_structure": "هيكل السوق",
        "details_current_trend": "الاتجاه الحالي ({timeframe})",
        "details_general_trend": "الاتجاه العام ({timeframe_parent})",
        "details_swing_high": "القمة المرجعية",
        "details_swing_low": "القاع المرجعي",
        "details_indicators_reading": "قراءة المؤشرات",
        "details_trend_strength": "قوة الاتجاه (ADX)",
        "details_momentum": "الزخم (RSI)",
        "details_macd": "التقارب والتباعد (MACD)",
        "details_confirmation_score": "مؤشرات القوة",
        "details_no_strength_reasons": "لا توجد مؤشرات قوة إضافية حاليًا.",
        "details_alternative_scenario": "السيناريو البديل",
        "details_cancellation_condition": "يتم إلغاء فكرة {signal_type} إذا تم كسر وقف الخسارة عند {stop_loss}. في هذه الحالة، قد يتجه السعر لاختبار المستوى التالي.",

        # --- Section 4: Support & Resistance ---
        "section_support_resistance_title": "--- 4. مستويات الدعم والمقاومة الرئيسية ---",
        "sr_resistance": "مقاومة",
        "sr_support": "دعم",

        # --- General Terms ---
        "signal_buy": "شراء",
        "signal_sell": "بيع",
        "signal_hold": "حياد",
        "trend_up": "صاعد",
        "trend_down": "هابط",
        "trend_sideways": "عرضي",
        "macd_positive": "تقاطع إيجابي",
        "macd_negative": "تقاطع سلبي",
        "strong_trend": "اتجاه قوي",
        "positive_momentum": "زخم إيجابي",
        "negative_momentum": "زخم سلبي",
        "compatible": "متوافق",
    },
    'en': {
        # --- Main Report Structure ---
        "report_title": "📊 **Comprehensive Strategic Analysis for {symbol} | {timeframe}**",
        "report_updated_at": "*Date: {date} | Time: {time}*",
        "disclaimer": "*Automated analysis, not direct investment advice.*",

        # --- Section 1: Executive Summary ---
        "section_summary_title": "--- 1. Executive Summary ---",
        "summary_signal": "Current Signal",
        "summary_conclusion": "Conclusion",
        "summary_key_level": "Key Level to Watch",

        # --- Section 2: Trade/Monitoring Plan ---
        "section_trade_plan_title": "--- 2. Suggested Trade Plan ---",
        "trade_logic": "Trade Rationale",
        "trade_risk_assessment": "Risk Assessment",
        "risk_to_reward": "Risk/Reward Ratio (for TP1)",
        "confidence": "Confidence Level",
        "entry_zone": "Entry Zone",
        "best_entry": "Best Entry Price",
        "stop_loss": "Stop Loss (SL)",
        "targets": "Targets (TP)",

        "section_monitoring_plan_title": "--- 2. Monitoring Plan ---",
        "monitoring_conclusion": "Current Situation",
        "monitoring_bullish_scenario": "Bullish Scenario (to watch)",
        "monitoring_bearish_scenario": "Bearish Scenario (to watch)",
        "monitoring_activation_condition": "Activation Condition",
        "monitoring_expected_targets": "Expected Targets",

        # --- Section 3: Technical Analysis Details ---
        "section_analysis_details_title": "--- 3. Technical Analysis Details ---",
        "details_market_structure": "Market Structure",
        "details_current_trend": "Current Trend ({timeframe})",
        "details_general_trend": "General Trend ({timeframe_parent})",
        "details_swing_high": "Swing High",
        "details_swing_low": "Swing Low",
        "details_indicators_reading": "Indicators Reading",
        "details_trend_strength": "Trend Strength (ADX)",
        "details_momentum": "Momentum (RSI)",
        "details_macd": "Convergence/Divergence (MACD)",
        "details_confirmation_score": "Confirmation Score",
        "details_no_strength_reasons": "No additional strength indicators are present currently.",
        "details_alternative_scenario": "Alternative Scenario",
        "details_cancellation_condition": "The {signal_type} idea is invalidated if the stop loss at {stop_loss} is breached. In this case, the price may test the next level.",

        # --- Section 4: Support & Resistance ---
        "section_support_resistance_title": "--- 4. Key Support & Resistance Levels ---",
        "sr_resistance": "Resistance",
        "sr_support": "Support",

        # --- General Terms ---
        "signal_buy": "Buy",
        "signal_sell": "Sell",
        "signal_hold": "Hold",
        "trend_up": "Upward",
        "trend_down": "Downward",
        "trend_sideways": "Sideways",
        "macd_positive": "Positive Crossover",
        "macd_negative": "Negative Crossover",
        "strong_trend": "Strong Trend",
        "positive_momentum": "Positive Momentum",
        "negative_momentum": "Negative Momentum",
        "compatible": "Compatible",
    }
}

def get_text(key: str, lang: str = "ar") -> str:
    lang_dict = TEXTS.get(lang, TEXTS.get("ar", {}))
    default_lang_dict = TEXTS.get("ar", {})
    return lang_dict.get(key, default_lang_dict.get(key, f"<{key}_NOT_FOUND>"))