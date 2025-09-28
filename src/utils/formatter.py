import os
from datetime import datetime
from typing import Dict, Any

def format_dynamic_price(price: float) -> str:
    """
    Formats a price with a dynamic number of decimal places and wraps it in bold markdown.
    """
    if not isinstance(price, (int, float)):
        return '**N/A**'

    if price > 10000:
        formatted_price = f"{price:,.0f}"
    elif price > 100:
        formatted_price = f"{price:,.2f}"
    elif price > 1:
        formatted_price = f"{price:,.4f}"
    else:
        formatted_price = f"{price:,.5f}"

    return f"**{formatted_price}**"


def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str) -> str:
    """
    Formats the analysis data into the 'Strategist' human-readable report.
    """
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

    trend = analysis_data.get('trend', 'N/A')
    trend_map = {'up': ('🔼', 'صاعد'), 'down': ('🔽', 'هابط')}
    trend_emoji, trend_text = trend_map.get(trend, ('↔️', 'عرضي'))

    # --- MTA Section ---
    mta_section = ""
    higher_tf_info = analysis_data.get('higher_tf_trend_info')
    if higher_tf_info:
        higher_tf_trend = higher_tf_info.get('trend', 'N/A')
        higher_tf_timeframe = higher_tf_info.get('timeframe', 'N/A')
        mta_emoji, mta_text = trend_map.get(higher_tf_trend, ('↔️', 'عرضي'))
        mta_section = f"- **الاتجاه على الإطار الأعلى ({higher_tf_timeframe}):** {mta_emoji} {mta_text}"

    signal = analysis_data.get('signal', 'HOLD')
    signal_map = {'BUY': ('🟢', 'شراء'), 'SELL': ('🔴', 'بيع'), 'HOLD': ('🟡', 'محايد')}
    signal_emoji, signal_text = signal_map.get(signal, ('⚪️', 'غير محدد'))

    zones = analysis_data.get('confluence_zones', [])
    confluence_zones_text = "\n".join([f"- {format_dynamic_price(zone['level'])} (تقاطع {zone['p_level']} و {zone['s_level']})" for zone in zones[:2]]) if zones else "- لا توجد مناطق توافق واضحة."
    reasons_text = "\n".join([f"- {reason}" for reason in analysis_data.get('reasons', [])]) if analysis_data.get('reasons') else "- لا توجد مؤشرات قوة حالياً."

    latest_data = analysis_data.get('latest_data', {})
    current_price = analysis_data.get('current_price', 0.0)
    key_levels = analysis_data.get('key_levels', [])
    key_levels_text = ""
    if key_levels:
        resistance_levels = sorted([lvl for lvl in key_levels if lvl['level'] > current_price], key=lambda x: x['level'])
        support_levels = sorted([lvl for lvl in key_levels if lvl['level'] <= current_price], key=lambda x: x['level'], reverse=True)

        if resistance_levels:
            key_levels_text += "**مقاومة:**\n" + "".join([f"- {format_dynamic_price(lvl['level'])} ({lvl['type']})\n" for lvl in resistance_levels])
        if support_levels:
            key_levels_text += "**دعم:**\n" + "".join([f"- {format_dynamic_price(lvl['level'])} ({lvl['type']})\n" for lvl in support_levels])
    if not key_levels_text:
        key_levels_text = "- لا توجد مستويات واضحة حالياً."
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    retracements = analysis_data.get('retracements', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    scenario2 = scenarios.get('scenario2', {})
    weights = analysis_data.get('weights', {})
    max_score = sum(weights.values()) if weights else 10 # Fallback max score

    final_reason_text = analysis_data.get('final_reason', 'لا يوجد سبب محدد.')

    # --- Dynamically build the suggested trade section ---
    suggested_trade_section = ""
    if signal in ['BUY', 'SELL']:
        rr_ratio_text = f"{analysis_data.get('rr_ratio', 0.0):.2f}:1" if analysis_data.get('rr_ratio', 0.0) > 0 else "N/A"
        suggested_trade_section = (
            f"**نوع الإشارة: {signal_emoji} {signal}**\n\n"
            f"**السيناريو الأساسي ({scenario1.get('title', 'N/A')})**\n"
            f"- **نقطة الدخول المقترحة:** {format_dynamic_price(scenario1.get('entry', 0.0))}\n"
            f"- **وقف الخسارة (SL):** {format_dynamic_price(scenario1.get('stop_loss', 0.0))}\n"
            f"- **الهدف (TP):** {format_dynamic_price(scenario1.get('target', 0.0))}\n"
            f"- **المخاطرة/العائد (RRR):** `{rr_ratio_text}`\n"
            f"- *نسبة النجاح المتوقعة: {scenario1.get('prob', 0)}%*\n\n"
            f"**السيناريو البديل ({scenario2.get('title', 'N/A')})**\n"
            f"- **نقطة التحول:** كسر مستوى {format_dynamic_price(scenario2.get('stop_loss', 0.0))}\n"
            f"- **الهدف في حالة الانعكاس:** {format_dynamic_price(scenario2.get('target', 0.0))}"
        )
    else: # HOLD signal
        swing_high_price_fmt = format_dynamic_price(swing_high.get('price', 0.0))
        swing_low_price_fmt = format_dynamic_price(swing_low.get('price', 0.0))

        final_reason_text = (
            f"السوق في حالة حياد. يُنصح بانتظار اختراق واضح. "
            f"يمكن مراقبة تفعيل إشارة **شراء** عند تجاوز مستوى {swing_high_price_fmt} "
            f"أو إشارة **بيع** عند كسر مستوى {swing_low_price_fmt}."
        )

        # Calculate potential R/R for HOLD scenarios
        entry_bullish = swing_high.get('price', 0.0)
        target_bullish = scenario1.get('target', 0.0)
        sl_bullish = scenario1.get('stop_loss', 0.0)

        profit_bullish = abs(target_bullish - entry_bullish)
        loss_bullish = abs(entry_bullish - sl_bullish)
        rr_bullish = f"`{profit_bullish / loss_bullish:.2f}:1`" if loss_bullish > 0 else "`N/A`"

        entry_bearish = swing_low.get('price', 0.0)
        target_bearish = scenario2.get('target', 0.0)
        sl_bearish = scenario2.get('stop_loss', 0.0)

        profit_bearish = abs(entry_bearish - target_bearish)
        loss_bearish = abs(sl_bearish - entry_bearish)
        rr_bearish = f"`{profit_bearish / loss_bearish:.2f}:1`" if loss_bearish > 0 else "`N/A`"

        suggested_trade_section = (
            f"**نوع الإشارة: {signal_emoji} {signal_text}**\n\n"
            "التحليل يشير إلى وضع محايد. فيما يلي السيناريوهات المحتملة للمراقبة:\n\n"
            f"**1. السيناريو الصاعد (توقع)**\n"
            f"- **شرط التفعيل:** الإغلاق اليومي فوق مستوى {swing_high_price_fmt}\n"
            f"- **الهدف:** {format_dynamic_price(target_bullish)}\n"
            f"- **وقف الخسارة:** {format_dynamic_price(sl_bullish)}\n"
            f"- **المخاطرة/العائد المحتملة:** {rr_bullish}\n\n"
            f"**2. السيناريو الهابط (توقع)**\n"
            f"- **شرط التفعيل:** الإغلاق اليومي أسفل مستوى {swing_low_price_fmt}\n"
            f"- **الهدف:** {format_dynamic_price(target_bearish)}\n"
            f"- **وقف الخسارة:** {format_dynamic_price(sl_bearish)}\n"
            f"- **المخاطرة/العائد المحتملة:** {rr_bearish}"
        )

    replacements = {
        "symbol": symbol, "timeframe": timeframe, "date": now.strftime('%Y/%m/%d'), "time": now.strftime('%H:%M:%S'),
        "current_price": format_dynamic_price(analysis_data.get('current_price', 0.0)),
        "trend_emoji": trend_emoji, "trend_text": trend_text,
        "mta_section": mta_section,
        "adx": f"**{latest_data.get('adx', 0.0):.2f}**", "rsi": f"**{latest_data.get('rsi', 0.0):.2f}**",
        "swing_high_price": format_dynamic_price(swing_high.get('price', 0.0)),
        "swing_low_price": format_dynamic_price(swing_low.get('price', 0.0)),
        "fib_618": format_dynamic_price(retracements.get('fib_618', 0.0)),
        "confluence_zones_text": confluence_zones_text,
        "key_levels_text": key_levels_text,
        "pattern": analysis_data.get('pattern', 'لا يوجد'),
        "score": f"{analysis_data.get('score', 0)}/{max_score}",
        "reasons_text": reasons_text,
        "final_reason": final_reason_text,
        "suggested_trade_section": suggested_trade_section,
    }

    class SafeFormatter(dict):
        def __missing__(self, key):
            return f'{{{key}}}'

    return template.format_map(SafeFormatter(replacements))