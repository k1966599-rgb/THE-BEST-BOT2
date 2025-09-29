# -*- coding: utf-8 -*-

# Centralized strings for the Telegram bot
# This makes it easier to manage, update, and translate the bot's text.

TEXTS = {
    'ar': {
        # --- Main Menu & Status ---
        "start_header": "**THE BEST BOT**\n\n",
        "bot_status_ok": "الحالة: يعمل ✅",
        "bot_status_periodic_disabled": "حالة البوت: يعمل بشكل طبيعي والتحليل الدوري معطل.",
        "button_analyze": "📊 تحليل",
        "button_bot_status": "ℹ️ حالة البوت",
        "button_back_to_main": "🔙 رجوع للقائمة الرئيسية",

        # --- Analysis Conversation ---
        "ask_symbol": "اختر العملة التي تريد تحليلها:",
        "ask_term": "تم اختيار {symbol}. الآن، اختر مدة التحليل:",
        "ask_timeframe": "اخترت {term}. الآن، اختر الإطار الزمني:",
        "analysis_running": "✅ شكراً لك! جاري تحليل {symbol} على إطار {timeframe}...",
        "fetching_data": "⏳ شكراً لك! جاري تحميل البيانات التاريخية لعملة {symbol} على إطار {timeframe}...",
        "fetching_parent_data": "⏳ جاري جلب بيانات الإطار الزمني الأعلى ({timeframe}) لتحديد الاتجاه العام...",
        "chart_generating": "🎨 جاري إعداد الرسم البياني...",
        "button_long_term": "مدى طويل",
        "button_medium_term": "مدى متوسط",
        "button_short_term": "مدى قصير",
        "button_back": "🔙 رجوع",

        # --- Periodic Analysis ---
        "periodic_start_log": "--- بدء التحليل الدوري لـ {count} عملة ---",
        "periodic_sent_alert_log": "تم إرسال تنبيه '{signal}' لعملة {symbol} على إطار {timeframe} إلى المدير.",
        "periodic_end_log": "--- اكتمل التحليل الدوري ---",
        "scheduler_disabled_log": "الجدولة معطلة. لن يتم إجراء التحليل التلقائي.",

        # --- Error & Warning Messages ---
        "error_generic": "حدث خطأ فني أثناء محاولة التحليل. يرجى مراجعة السجلات.",
        "error_config_timeframes": "خطأ في الإعدادات: لم يتم العثور على أطر زمنية لهذا الاختيار.",
        "error_data_fetch": "عذراً، لم أتمكن من جلب البيانات لهذه العملة. يرجى المحاولة مرة أخرى.",
        "error_no_token": "لم يتم العثور على توكن البوت (BOT_TOKEN) في ملف .env.",
        "warning_no_admin_id": "لم يتم تعيين TELEGRAM_ADMIN_CHAT_ID. سيتم تخطي التنبيهات الدورية.",
        "error_api_connection": "لا يمكن الوصول إلى خادم البيانات حاليًا. يرجى المحاولة مرة أخرى لاحقًا.",
        "error_invalid_symbol": "الرمز '{symbol}' غير صالح أو غير مدعوم من قبل مزود البيانات.",
        "error_unknown_api": "حدث خطأ غير متوقع من مزود البيانات. ({status_code})",
        "error_not_enough_historical_data": "⚠️ عذراً، لا توجد بيانات تاريخية كافية لتحليل {symbol} على إطار {timeframe}.\n\nيرجى محاولة استخدام إطار زمني أطول (مثل 1D أو 1W).",
        "error_not_enough_data_detailed": "⚠️ عذراً، لا توجد بيانات كافية لتحليل {symbol} على إطار {timeframe}. (مطلوب: {required} شمعة، متوفر: {available})",

        # --- Bot Control ---
        "bot_starting_log": "جاري تشغيل بوت التليجرام...",
    },
    'en': {
        # --- Main Menu & Status ---
        "start_header": "**THE BEST BOT**\n\n",
        "bot_status_ok": "Status: Running ✅",
        "bot_status_periodic_disabled": "Bot status: Normal operation, periodic analysis is disabled.",
        "button_analyze": "📊 Analyze",
        "button_bot_status": "ℹ️ Bot Status",
        "button_back_to_main": "🔙 Back to Main Menu",

        # --- Analysis Conversation ---
        "ask_symbol": "Select the currency you want to analyze:",
        "ask_term": "{symbol} selected. Now, choose the analysis term:",
        "ask_timeframe": "You chose {term}. Now, select the timeframe:",
        "analysis_running": "✅ Thank you! Analyzing {symbol} on the {timeframe} timeframe...",
        "fetching_data": "⏳ Thank you! Fetching historical data for {symbol} on the {timeframe} timeframe...",
        "fetching_parent_data": "⏳ Fetching higher timeframe data ({timeframe}) to determine the general trend...",
        "chart_generating": "🎨 Generating chart...",
        "button_long_term": "Long Term",
        "button_medium_term": "Medium Term",
        "button_short_term": "Short Term",
        "button_back": "🔙 Back",

        # --- Periodic Analysis ---
        "periodic_start_log": "--- Starting Periodic Analysis for {count} symbols ---",
        "periodic_sent_alert_log": "Sent '{signal}' alert for {symbol} on {timeframe} to admin.",
        "periodic_end_log": "--- Periodic Analysis Complete ---",
        "scheduler_disabled_log": "Scheduler is configured but DISABLED. Automatic analysis will not run.",

        # --- Error & Warning Messages ---
        "error_generic": "A technical error occurred during the analysis. Please check the logs.",
        "error_config_timeframes": "Configuration Error: No timeframes found for this selection.",
        "error_data_fetch": "Sorry, I could not fetch the data for this currency. Please try again.",
        "error_no_token": "Telegram BOT_TOKEN not found in .env file.",
        "warning_no_admin_id": "TELEGRAM_ADMIN_CHAT_ID not set. Periodic alerts will be skipped.",
        "error_api_connection": "Could not reach the data server at this time. Please try again later.",
        "error_invalid_symbol": "The symbol '{symbol}' is invalid or not supported by the data provider.",
        "error_unknown_api": "An unexpected error occurred from the data provider. ({status_code})",
        "error_not_enough_historical_data": "⚠️ Sorry, not enough historical data to analyze {symbol} on the {timeframe} timeframe.\n\nPlease try a longer timeframe (e.g., 1D or 1W).",
        "error_not_enough_data_detailed": "⚠️ Sorry, not enough data to analyze {symbol} on the {timeframe} timeframe. (Required: {required} candles, Available: {available})",

        # --- Bot Control ---
        "bot_starting_log": "Starting Telegram bot...",
    }
}

# Helper function to get a string in a specific language
def get_text(key: str, lang: str = "ar") -> str:
    """
    Retrieves a text string from the TEXTS dictionary.
    Defaults to 'ar' language if the requested language or key is not found.
    """
    # Fallback to 'ar' if the language doesn't exist
    lang_dict = TEXTS.get(lang, TEXTS["ar"])
    return lang_dict.get(key, TEXTS["ar"].get(key, f"<{key}_NOT_FOUND>"))