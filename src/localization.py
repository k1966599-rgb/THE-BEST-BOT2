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
        "monitoring_conclusion": "الخلاصة",
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
        "details_confirmation_score": "نقاط القوة",
        "details_no_strength_reasons": "لا توجد نقاط قوة إضافية حاليًا.",
        "details_alternative_scenario": "السيناريو البديل وإلغاء الفكرة",
        "details_cancellation_condition": "تُلغى فكرة {signal_type} بكسر وقف الخسارة عند {stop_loss}، وقد يتجه السعر بعدها لاختبار مناطق أدنى.",

        # --- Section 4: Support & Resistance ---
        "section_support_resistance_title": "--- 4. مستويات الدعم والمقاومة ---",
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

        # --- Analysis Reasons & Conclusions (from FiboAnalyzer) ---
        "reason_rsi_confirm_up": "مؤشر القوة النسبية فوق 50 (القيمة: {value})",
        "reason_macd_confirm_up": "تقاطع MACD إيجابي",
        "reason_stoch_confirm_up": "مؤشر ستوكاستيك يظهر انعكاسًا من التشبع البيعي",
        "reason_pattern_confirm_up": "نموذج انعكاسي صاعد: {pattern}",
        "reason_rsi_confirm_down": "مؤشر القوة النسبية تحت 50 (القيمة: {value})",
        "reason_macd_confirm_down": "تقاطع MACD سلبي",
        "reason_stoch_confirm_down": "مؤشر ستوكاستيك يظهر انعكاسًا من التشبع الشرائي",
        "reason_pattern_confirm_down": "نموذج انعكاسي هابط: {pattern}",
        "reason_volume_confirm_up": "تأكيد طفرة حجم تداول صاعدة",
        "reason_volume_confirm_down": "تأكيد طفرة حجم تداول هابطة",

        "final_reason_signal_confirmed": "بناءً على {score} نقطة قوة مع اتجاه {trend} مؤكد.",
        "final_reason_score_met_adx_weak": "تم تحقيق النقاط المطلوبة لكن قوة الاتجاه ضعيفة (ADX: {adx})",
        "final_reason_score_not_met": "لم يتم تحقيق الحد الأدنى من نقاط القوة ({score}/{threshold})، لذا يتم انتظار إشارة أوضح.",
        "final_reason_mta_override": "تم تعليق إشارة {original_signal} بسبب تعارضها مع الاتجاه العام الهابط على إطار {higher_tf}.",

        "scenario_title_up_primary": "السيناريو الصاعد الأساسي",
        "scenario_title_up_secondary": "السيناريو الهابط البديل",
        "scenario_title_down_primary": "السيناريو الهابط الأساسي",
        "scenario_title_down_secondary": "السيناريو الصاعد البديل",
        "scenario_title_up_primary_hold": "السيناريو الصاعد المحتمل",
        "scenario_title_up_secondary_hold": "السيناريو الهابط المحتمل",
        "scenario_title_down_primary_hold": "السيناريو الهابط المحتمل",
        "scenario_title_down_secondary_hold": "السيناريو الصاعد المحتمل",

        # --- Error Messages ---
        "error_no_valid_swings": "تعذر تحديد قمم وقيعان واضحة للتحليل. يرجى تجربة إطار زمني مختلف.",
        "error_not_enough_data_detailed": "لا توجد بيانات كافية لـ {symbol} على إطار {timeframe}. (مطلوب: {required}, متاح: {available})",
        "error_not_enough_historical_data": "لا توجد بيانات تاريخية كافية لـ {symbol} على إطار {timeframe}.",
        "error_api_connection": "حدث خطأ أثناء الاتصال بواجهة برمجة التطبيقات. يرجى المحاولة مرة أخرى لاحقًا.",
        "error_generic": "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
        "error_config_timeframes": "خطأ في الإعدادات: لم يتم العثور على أطر زمنية للمدى المحدد.",
        "error_no_token": "خطأ فادح: رمز بوت تليجرام غير موجود في الإعدادات.",

        # --- UI Buttons ---
        "button_analyze": "تحليل",
        "button_bot_status": "متابعة التحليل",
        "button_back_to_main": "العودة للقائمة الرئيسية",
        "button_back": "رجوع",
        "button_long_term": "طويل",
        "button_medium_term": "متوسط",
        "button_short_term": "قصير",

        # --- UI Messages ---
        "start_header": "",
        "bot_status_ok": "يعمل",
        "bot_status_periodic_disabled": "متابعة التحليل: معطلة حاليًا.",
        "ask_symbol": "اختر العملة التي تريد تحليلها:",
        "ask_term": "اختر المدى الزمني للتحليل لـ {symbol}:",
        "ask_timeframe": "اختر الإطار الزمني للتحليل على {term}:",

        # --- Process/Log Messages ---
        "fetching_parent_data": "جاري جلب بيانات الإطار الزمني الأعلى ({timeframe})...",
        "fetching_data": "جاري جلب البيانات لـ {symbol} على إطار {timeframe}...",
        "analysis_running": "جاري إجراء التحليل لـ {symbol} على إطار {timeframe}...",
        "chart_generating": "جاري إنشاء الرسم البياني...",
        "warning_no_admin_id": "تحذير: معرف المشرف غير محدد، لن يتم إرسال التنبيهات الدورية.",
        "periodic_start_log": "بدء مهمة التحليل الدوري لـ {count} عملة.",
        "periodic_sent_alert_log": "تم إرسال تنبيه {signal} لـ {symbol} على إطار {timeframe}.",
        "periodic_end_log": "اكتملت مهمة التحليل الدوري.",
        "scheduler_disabled_log": "الجدولة الدورية معطلة في الإعدادات.",
        "bot_starting_log": "البوت قيد التشغيل..."
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
        "monitoring_conclusion": "Conclusion",
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
        "details_confirmation_score": "Strength Score",
        "details_no_strength_reasons": "No additional strength indicators are currently present.",
        "details_alternative_scenario": "Alternative Scenario & Invalidation",
        "details_cancellation_condition": "The {signal_type} idea is invalidated if the stop loss at {stop_loss} is breached, after which the price may test lower levels.",

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

        # --- Analysis Reasons & Conclusions (from FiboAnalyzer) ---
        "reason_rsi_confirm_up": "RSI is above 50 (Value: {value})",
        "reason_macd_confirm_up": "Positive MACD Crossover",
        "reason_stoch_confirm_up": "Stochastic shows reversal from oversold",
        "reason_pattern_confirm_up": "Bullish reversal pattern: {pattern}",
        "reason_rsi_confirm_down": "RSI is below 50 (Value: {value})",
        "reason_macd_confirm_down": "Negative MACD Crossover",
        "reason_stoch_confirm_down": "Stochastic shows reversal from overbought",
        "reason_pattern_confirm_down": "Bearish reversal pattern: {pattern}",
        "reason_volume_confirm_up": "Bullish volume spike confirmed",
        "reason_volume_confirm_down": "Bearish volume spike confirmed",

        "final_reason_signal_confirmed": "Based on {score} strength points with a confirmed {trend} trend.",
        "final_reason_score_met_adx_weak": "Required score met, but trend strength is weak (ADX: {adx})",
        "final_reason_score_not_met": "Minimum strength score not met ({score}/{threshold}), waiting for a clearer signal.",
        "final_reason_mta_override": "The {original_signal} signal is suspended due to conflict with the bearish trend on the {higher_tf} timeframe.",

        "scenario_title_up_primary": "Primary Bullish Scenario",
        "scenario_title_up_secondary": "Alternative Bearish Scenario",
        "scenario_title_down_primary": "Primary Bearish Scenario",
        "scenario_title_down_secondary": "Alternative Bullish Scenario",
        "scenario_title_up_primary_hold": "Potential Bullish Scenario",
        "scenario_title_up_secondary_hold": "Potential Bearish Scenario",
        "scenario_title_down_primary_hold": "Potential Bearish Scenario",
        "scenario_title_down_secondary_hold": "Potential Bullish Scenario",

        # --- Error Messages ---
        "error_no_valid_swings": "Could not determine clear swing points for analysis. Please try a different timeframe.",
        "error_not_enough_data_detailed": "Not enough data for {symbol} on {timeframe}. (Required: {required}, Available: {available})",
        "error_not_enough_historical_data": "Not enough historical data for {symbol} on {timeframe}.",
        "error_api_connection": "An error occurred while connecting to the API. Please try again later.",
        "error_generic": "An unexpected error occurred. Please try again.",
        "error_config_timeframes": "Configuration Error: No timeframes found for the selected term.",
        "error_no_token": "Fatal Error: Telegram bot token not found in configuration.",

        # --- UI Buttons ---
        "button_analyze": "Analysis",
        "button_bot_status": "Follow-up Analysis",
        "button_back_to_main": "Back to Main Menu",
        "button_back": "Back",
        "button_long_term": "Long",
        "button_medium_term": "Medium",
        "button_short_term": "Short",

        # --- UI Messages ---
        "start_header": "Welcome to THE BEST BOT",
        "bot_status_ok": "Bot Status: Online.",
        "bot_status_periodic_disabled": "Follow-up analysis is currently disabled.",
        "ask_symbol": "Select the symbol to analyze:",
        "ask_term": "Select the analysis term for {symbol}:",
        "ask_timeframe": "Select the timeframe for analysis on the {term}:",

        # --- Process/Log Messages ---
        "fetching_parent_data": "Fetching parent timeframe data ({timeframe})...",
        "fetching_data": "Fetching data for {symbol} on {timeframe}...",
        "analysis_running": "Running analysis for {symbol} on {timeframe}...",
        "chart_generating": "Generating chart...",
        "warning_no_admin_id": "Warning: Admin chat ID not set, periodic alerts will not be sent.",
        "periodic_start_log": "Starting periodic analysis task for {count} symbols.",
        "periodic_sent_alert_log": "Sent {signal} alert for {symbol} on {timeframe}.",
        "periodic_end_log": "Periodic analysis task completed.",
        "scheduler_disabled_log": "Periodic scheduler is disabled in settings.",
        "bot_starting_log": "Bot is starting..."
    }
}

def get_text(key: str, lang: str = "ar") -> str:
    lang_dict = TEXTS.get(lang, TEXTS.get("ar", {}))
    default_lang_dict = TEXTS.get("ar", {})
    return lang_dict.get(key, default_lang_dict.get(key, f"<{key}_NOT_FOUND>"))