import os
from datetime import datetime
from typing import Dict, Any

def format_dynamic_price(price: float) -> str:
    """
    Formats a price with a dynamic number of decimal places and wraps it in backticks.
    - No decimals for prices > 10000 (like BTC)
    - 2 decimals for prices > 100
    - 4 decimals for prices > 1
    - 5 decimals for prices <= 1 (like DOGE)
    """
    if not isinstance(price, (int, float)):
        return '`N/A`'

    if price > 10000:
        formatted_price = f"{price:,.0f}"
    elif price > 100:
        formatted_price = f"{price:,.2f}"
    elif price > 1:
        formatted_price = f"{price:,.4f}"
    else:
        formatted_price = f"{price:,.5f}"

    return f"`{formatted_price}`"


def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str) -> str:
    """
    Formats the analysis data into the 'Strategist' human-readable report.
    """
    # Handle cases where analysis was stopped prematurely
    reason = analysis_data.get('reason')
    if reason:
        return (
            f"📊 **تحليل {symbol} | {timeframe}**\n\n"
            f"**⚠️ تم إيقاف التحليل.**\n"
            f"**السبب:** {reason}"
        )

    template_path = os.path.join('src', 'templates', 'analysis_template.md')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return "خطأ: قالب التحليل غير موجود."

    now = datetime.now()

    # --- Prepare data for the template ---

    # Trend
    trend = analysis_data.get('trend', 'N/A')
    trend_map = {'up': ('🔼', 'صاعد'), 'down': ('🔽', 'هابط')}
    trend_emoji, trend_text = trend_map.get(trend, ('↔️', 'عرضي'))

    # Signal
    signal = analysis_data.get('signal', 'HOLD')
    signal_map = {'BUY': ('🟢', 'شراء'), 'SELL': ('🔴', 'بيع'), 'HOLD': ('🟡', 'محايد')}
    signal_emoji, signal_text = signal_map.get(signal, ('⚪️', 'غير محدد'))

    # Confluence Zones
    zones = analysis_data.get('confluence_zones', [])
    if zones:
        # Use the new dynamic formatter for zone levels
        confluence_zones_text = "\n".join([f"- {format_dynamic_price(zone['level'])} (تقاطع {zone['p_level']} و {zone['s_level']})" for zone in zones[:2]])
    else:
        confluence_zones_text = "- لا توجد مناطق توافق واضحة."

    # Reasons
    reasons = analysis_data.get('reasons', [])
    if reasons:
        reasons_text = "\n".join([f"- {reason}" for reason in reasons])
    else:
        reasons_text = "- لا توجد مؤشرات قوة حالياً."

    # --- Build Replacements Dictionary ---
    latest_data = analysis_data.get('latest_data', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    retracements = analysis_data.get('retracements', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    scenario2 = scenarios.get('scenario2', {})

    replacements = {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": now.strftime('%Y/%m/%d'),
        "time": now.strftime('%H:%M:%S'),

        "current_price": format_dynamic_price(analysis_data.get('current_price', 0.0)),
        "trend_emoji": trend_emoji,
        "trend_text": trend_text,
        "adx": f"`{latest_data.get('adx', 0.0):.2f}`",
        "rsi": f"`{latest_data.get('rsi', 0.0):.2f}`",

        "swing_high_price": format_dynamic_price(swing_high.get('price', 0.0)),
        "swing_low_price": format_dynamic_price(swing_low.get('price', 0.0)),
        "fib_618": format_dynamic_price(retracements.get('fib_618', 0.0)),
        "confluence_zones_text": confluence_zones_text,

        "pattern": analysis_data.get('pattern', 'لا يوجد'),
        "score": f"{analysis_data.get('score', 0)}/10",
        "reasons_text": reasons_text,

        "signal_emoji": signal_emoji,
        "signal": signal_text,

        "scenario1_title": scenario1.get('title', 'N/A'),
        "scenario1_entry": format_dynamic_price(scenario1.get('entry', 0.0)),
        "scenario1_stop_loss": format_dynamic_price(scenario1.get('stop_loss', 0.0)),
        "scenario1_target": format_dynamic_price(scenario1.get('target', 0.0)),
        "scenario1_prob": f"{scenario1.get('prob', 0)}%",

        "scenario1_title": scenario1.get('title', 'N/A'),
        "scenario1_entry": format_dynamic_price(scenario1.get('entry', 0.0)),
        "scenario1_stop_loss": format_dynamic_price(scenario1.get('stop_loss', 0.0)),
        "scenario1_target": format_dynamic_price(scenario1.get('target', 0.0)),
        "scenario1_prob": f"{scenario1.get('prob', 0)}%",

        "scenario2_title": scenario2.get('title', 'N/A'),
        "scenario2_stop_loss": format_dynamic_price(scenario2.get('stop_loss', 0.0)),
        "scenario2_target": format_dynamic_price(scenario2.get('target', 0.0)),
    }

    # --- Dynamically build the suggested trade section ---
    suggested_trade_section = ""
    if signal in ['BUY', 'SELL']:
        rr_ratio = analysis_data.get('rr_ratio', 0.0)
        rr_ratio_text = f"{rr_ratio}:1" if rr_ratio > 0 else "N/A"
        suggested_trade_section = (
            f"**نوع الإشارة: {signal_emoji} {signal}**\n\n"
            f"**السيناريو الأساسي ({replacements['scenario1_title']})**\n"
            f"- **نقطة الدخول المقترحة:** {replacements['scenario1_entry']}\n"
            f"- **وقف الخسارة (SL):** {replacements['scenario1_stop_loss']}\n"
            f"- **الهدف (TP):** {replacements['scenario1_target']}\n"
            f"- **المخاطرة/العائد (RRR):** `{rr_ratio_text}`\n"
            f"- *نسبة النجاح المتوقعة: {replacements['scenario1_prob']}*\n\n"
            f"**السيناريو البديل ({replacements['scenario2_title']})**\n"
            f"- **نقطة التحول:** كسر مستوى {replacements['scenario2_stop_loss']}\n"
            f"- **الهدف في حالة الانعكاس:** {replacements['scenario2_target']}"
        )
    else: # HOLD signal
        suggested_trade_section = (
            f"**نوع الإشارة: {signal_emoji} {signal}**\n\n"
            "التحليل يشير إلى وضع محايد في الوقت الحالي. لا توجد إشارة واضحة للشراء أو البيع. "
            "فيما يلي السيناريوهات المحتملة:\n\n"
            f"**1. {replacements['scenario1_title']} ({replacements['scenario1_prob']})**\n"
            f"- **الهدف:** {replacements['scenario1_target']}\n"
            f"- **نقطة إبطال السيناريو:** {replacements['scenario1_stop_loss']}\n\n"
            f"**2. {replacements['scenario2_title']} ({100 - scenario1.get('prob', 0)}%)**\n"
            f"- **الهدف:** {replacements['scenario2_target']}\n"
            f"- **نقطة إبطال السيناريو:** {replacements['scenario2_stop_loss']}"
        )

    replacements['suggested_trade_section'] = suggested_trade_section


    # Using format_map with a custom dict to avoid crashing on any other missing keys
    class SafeFormatter(dict):
        def __missing__(self, key):
            # Returns the key surrounded by braces, so it's visible in the output
            return f'{{{key}}}'

    return template.format_map(SafeFormatter(replacements))
