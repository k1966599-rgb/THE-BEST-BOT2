# -*- coding: utf-8 -*-

# Centralized strings for the Telegram bot
# This makes it easier to manage, update, and potentially translate the bot's text.

TEXTS = {
    "AR": {
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
        "button_long_term": "مدى طويل",
        "button_medium_term": "مدى متوسط",
        "button_short_term": "مدى قصير",
        "button_back": "🔙 رجوع",

        # --- Periodic Analysis ---
        "periodic_start_log": "--- Starting Periodic Analysis for {count} symbols ---",
        "periodic_sent_alert_log": "Sent '{signal}' alert for {symbol} on {timeframe} to admin.",
        "periodic_end_log": "--- Periodic Analysis Complete ---",
        "scheduler_disabled_log": "Scheduler is configured but DISABLED. Automatic analysis will not run.",

        # --- Error & Warning Messages ---
        "error_generic": "حدث خطأ فني أثناء محاولة التحليل. يرجى مراجعة السجلات.",
        "error_config_timeframes": "خطأ في الإعدادات: لم يتم العثور على أطر زمنية لهذا الاختيار.",
        "error_data_fetch": "عذراً، لم أتمكن من جلب البيانات لهذه العملة. يرجى المحاولة مرة أخرى.",
        "error_no_token": "Telegram BOT_TOKEN not found in .env file.",
        "warning_no_admin_id": "TELEGRAM_ADMIN_CHAT_ID not set. Periodic alerts will be skipped.",
        "error_api_connection": "لا يمكن الوصول إلى خادم البيانات حاليًا. يرجى المحاولة مرة أخرى لاحقًا.",
        "error_invalid_symbol": "الرمز '{symbol}' غير صالح أو غير مدعوم من قبل مزود البيانات.",
        "error_unknown_api": "حدث خطأ غير متوقع من مزود البيانات. ({status_code})",
        "error_not_enough_historical_data": "⚠️ عذراً، لا توجد بيانات تاريخية كافية لتحليل {symbol} على إطار {timeframe}.\n\nيرجى محاولة استخدام إطار زمني أطول.",
        "error_not_enough_data_detailed": "⚠️ عذراً، لا توجد بيانات كافية لتحليل {symbol} على إطار {timeframe}.\n\n*التفاصيل:*\n- الشموع المطلوبة للتحليل: `{required}`\n- الشموع المتاحة بعد المعالجة: `{available}`\n\nقد يكون السبب مشكلة مؤقتة في جلب البيانات من المنصة. يرجى المحاولة مرة أخرى.",

        # --- Account Info ---
        "fetching_balance": "⏳ جاري جلب بيانات الرصيد...",
        "balance_header": "*--- 💰 رصيد حسابك ---*",
        "balance_line_item": "\n`{asset}`\n*الإجمالي:* `{total}`\n*المتاح:* `{available}` | *المجمد:* `{frozen}`",
        "no_assets_found": "لم يتم العثور على أي عملات ذات رصيد في حسابك.",
        "error_fetching_balance": "حدث خطأ أثناء جلب بيانات الرصيد.",

        "fetching_positions": "⏳ جاري جلب بيانات الصفقات المفتوحة...",
        "positions_header": "*--- 📈 صفقاتك المفتوحة ---*",
        "position_line_item": "\n*{instrument}* | `{side}`\n*الحجم:* `{size}`\n*سعر الدخول:* `{entry_price}`\n*الرافعة:* `x{leverage}`\n*الربح/الخسارة:* `{pnl_sign} {pnl} USDT`",
        "no_open_positions": "لا توجد لديك أي صفقات مفتوحة حاليًا.",
        "error_fetching_positions": "حدث خطأ أثناء جلب بيانات الصفقات المفتوحة.",
        "position_side_long": "شراء",
        "position_side_short": "بيع",
        "position_side_net": "محايد",

        # --- Bot Control ---
        "bot_starting_log": "Starting Telegram bot...",
    }
}

# Helper function to get a string in a specific language
def get_text(key: str, lang: str = "AR") -> str:
    """
    Retrieves a text string from the TEXTS dictionary.
    Defaults to 'AR' language if the requested language is not found.
    """
    return TEXTS.get(lang, TEXTS["AR"]).get(key, f"<{key}_NOT_FOUND>")