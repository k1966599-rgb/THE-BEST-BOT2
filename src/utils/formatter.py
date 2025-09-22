import os
from datetime import datetime
from typing import Dict, Any

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str) -> str:
    """
    Formats the analysis data into the 'Strategist' human-readable report.
    """
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
        confluence_zones_text = "\n".join([f"- **${zone['level']:.4f}** (تقاطع {zone['p_level']} و {zone['s_level']})" for zone in zones[:2]])
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

        "current_price": analysis_data.get('current_price', 0.0),
        "trend_emoji": trend_emoji,
        "trend_text": trend_text,
        "adx": latest_data.get('adx', 0.0),
        "rsi": latest_data.get('rsi', 0.0),

        "swing_high_price": swing_high.get('price', 0.0),
        "swing_low_price": swing_low.get('price', 0.0),
        "fib_618": retracements.get('fib_618', 0.0),
        "confluence_zones_text": confluence_zones_text,

        "pattern": analysis_data.get('pattern', 'لا يوجد'),
        "score": analysis_data.get('score', 0),
        "reasons_text": reasons_text,

        "signal_emoji": signal_emoji,
        "signal": signal_text,

        "scenario1_title": scenario1.get('title', 'N/A'),
        "scenario1_entry": scenario1.get('entry', 0.0),
        "scenario1_stop_loss": scenario1.get('stop_loss', 0.0),
        "scenario1_target": scenario1.get('target', 0.0),
        "scenario1_prob": scenario1.get('prob', 0),

        "scenario2_title": scenario2.get('title', 'N/A'),
        "scenario2_stop_loss": scenario2.get('stop_loss', 0.0),
        "scenario2_target": scenario2.get('target', 0.0),
    }

    # Using format_map with a custom dict to avoid crashing on any other missing keys
    class SafeFormatter(dict):
        def __missing__(self, key):
            # Returns the key surrounded by braces, so it's visible in the output
            return f'{{{key}}}'

    return template.format_map(SafeFormatter(replacements))
