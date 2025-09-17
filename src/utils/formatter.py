import os
from datetime import datetime
from typing import Dict, Any, Tuple

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str) -> str:
    """
    Formats the new analysis data into the redesigned human-readable report.
    """
    template_path = os.path.join('src', 'templates', 'analysis_template.md')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return "Error: Analysis template not found."

    now = datetime.now()

    # --- Helper for safe formatting ---
    def format_price(price):
        return f"${price:.2f}" if price and isinstance(price, (int, float)) and price > 0 else "غير متاح"

    # --- Main Signal ---
    signal = analysis_data.get('signal', 'HOLD')
    signal_map = {'BUY': ('🟢', 'شراء'), 'SELL': ('🔴', 'بيع'), 'HOLD': ('🟡', 'محايد')}
    signal_emoji, signal_text = signal_map.get(signal, ('⚪️', 'غير محدد'))

    # --- Trend ---
    trend = analysis_data.get('trend', 'N/A')
    trend_emoji = '🔼' if trend == 'up' else '🔽'

    # --- Fibonacci Levels ---
    retracements = analysis_data.get('retracements', {})
    extensions = analysis_data.get('extensions', {})

    # --- Risk Levels ---
    risk_levels = analysis_data.get('risk_levels', {})

    # --- Build Replacements Dictionary ---
    replacements = {
        "timeframe": timeframe,
        "symbol": symbol,
        "date": now.strftime('%Y/%m/%d'),
        "time": now.strftime('%H:%M:%S'),
        "signal_emoji": signal_emoji,
        "signal_text": signal_text,
        "reason": analysis_data.get('reason', 'لا توجد أسباب واضحة.'),
        "score": analysis_data.get('score', 0),
        "trend_emoji": trend_emoji,
        "trend": "صاعد" if trend == 'up' else "هابط",
        "current_price": format_price(analysis_data.get('current_price')),
        "swing_high_price": format_price(analysis_data.get('swing_high', {}).get('price')),
        "swing_low_price": format_price(analysis_data.get('swing_low', {}).get('price')),

        "fib_236": format_price(retracements.get('fib_236')),
        "fib_382": format_price(retracements.get('fib_382')),
        "fib_500": format_price(retracements.get('fib_500')),
        "fib_618": format_price(retracements.get('fib_618')),
        "fib_786": format_price(retracements.get('fib_786')),
        "fib_886": format_price(retracements.get('fib_886')),

        "ext_1272": format_price(extensions.get('ext_1272')),
        "ext_1618": format_price(extensions.get('ext_1618')),
        "ext_2000": format_price(extensions.get('ext_2000')),
        "ext_2618": format_price(extensions.get('ext_2618')),

        "pattern": analysis_data.get('pattern', 'لا يوجد'),
        "entry_point": format_price(risk_levels.get('entry')),
        "stop_loss": format_price(risk_levels.get('stop_loss')),
        "target_1": format_price(risk_levels.get('targets', [None])[0]),
        "target_2": format_price(risk_levels.get('targets', [None, None])[1]),
    }

    return template.format(**replacements)
