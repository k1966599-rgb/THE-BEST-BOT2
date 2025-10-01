import os
from datetime import datetime
from typing import Dict, Any
from src.config import get_config

def format_dynamic_price(price: float) -> str:
    """Formats a price with a dynamic number of decimal places as a plain string."""
    if not isinstance(price, (int, float)) or price == 0:
        return 'N/A'
    if price > 10000:
        return f"{price:,.0f}"
    if price > 100:
        return f"{price:,.2f}"
    if price > 1:
        return f"{price:,.4f}"
    return f"{price:,.6f}"

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str, lang: str = "ar") -> str:
    """
    Formats the analysis data into a clean, text-based report based on the final template.
    """
    config = get_config()
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    # Determine which template to use
    term = 'long_term'
    if timeframe in timeframe_groups.get('short_term', []):
        term = 'short_term'
    elif timeframe in timeframe_groups.get('medium_term', []):
        term = 'medium_term'

    template_filename = f'{term}_template.md'
    template_path = os.path.join('src', 'templates', template_filename)

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return f"Error: Template '{template_filename}' not found."
    except Exception as e:
        return f"Error reading template: {e}"

    # --- Safe Data Extraction ---
    latest_data = analysis_data.get('latest_data', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    signal = analysis_data.get('signal', 'HOLD')
    final_reason = analysis_data.get('final_reason')
    retracements = analysis_data.get('retracements', {})
    key_support = analysis_data.get('key_support', {})
    key_resistance = analysis_data.get('key_resistance', {})
    swing_high = analysis_data.get('swing_high', {}).get('price')
    swing_low = analysis_data.get('swing_low', {}).get('price')
    fibo_trend = analysis_data.get('fibo_trend', 'up') # Default to 'up' if not present

    # --- Smart Summary Interpretation ---
    summary_text = "لا توجد إشارة واضحة حاليًا. يوصى بالمراقبة."
    if final_reason and isinstance(final_reason, dict):
        reason_key = final_reason.get('key')
        if reason_key == 'final_reason_signal_confirmed':
            summary_text = f"إشارة {signal.lower()} قوية مدعومة بتوافق المؤشرات الفنية."
        elif reason_key == 'final_reason_score_met_adx_weak':
            summary_text = f"إشارة {signal.lower()} محتملة، لكن قوة الاتجاه ضعيفة. يوصى بالحذر."
        elif reason_key == 'final_reason_mta_override':
            original_signal = final_reason.get('context', {}).get('original_signal', 'N/A')
            summary_text = f"تم إلغاء إشارة {original_signal} بسبب تعارضها مع اتجاه الإطار الزمني الأعلى."

    # --- Indicator Interpretation ---
    adx_value = latest_data.get('adx', 0)
    adx_interpretation = "قوي" if adx_value >= 25 else "ضعيف أو عرضي"

    # --- Conditional Trade Recommendation Section ---
    trade_recommendation_section = ""
    if signal in ['BUY', 'SELL']:
        entry_price = format_dynamic_price(scenario1.get('entry_zone', {}).get('best'))
        stop_loss = format_dynamic_price(scenario1.get('stop_loss'))
        targets = scenario1.get('targets', {})
        target_1 = format_dynamic_price(targets.get('tp1'))
        target_2 = format_dynamic_price(targets.get('tp2'))

        recommendation_lines = [
            "\n--- صفقة مقترحة ---",
            f"الدخول:         {entry_price}",
            f"وقف الخسارة:    {stop_loss}",
            f"الهدف الأول:     {target_1}",
            f"الهدف الثاني:    {target_2}"
        ]
        trade_recommendation_section = "\n".join(recommendation_lines)

    # --- Final Replacements Dictionary ---
    replacements = {
        "symbol": symbol,
        "timeframe": timeframe,
        "trend": str(analysis_data.get('trend', 'N/A')).upper(),
        "adx_value": f"{adx_value:.2f}",
        "adx_interpretation": adx_interpretation,
        "key_support_price": format_dynamic_price(key_support.get('level')),
        "key_support_type": key_support.get('type', 'N/A'),
        "key_resistance_price": format_dynamic_price(key_resistance.get('level')),
        "key_resistance_type": key_resistance.get('type', 'N/A'),
        "fib_1": format_dynamic_price(swing_high if fibo_trend == 'up' else swing_low),
        "fib_0": format_dynamic_price(swing_low if fibo_trend == 'up' else swing_high),
        "fib_618": format_dynamic_price(retracements.get('fib_618')),
        "fib_500": format_dynamic_price(retracements.get('fib_500')),
        "fib_382": format_dynamic_price(retracements.get('fib_382')),
        "signal": signal,
        "confidence_score": f"{analysis_data.get('confidence', 50):.0f}",
        "summary": summary_text,
        "trade_recommendation_section": trade_recommendation_section,
    }

    class SafeFormatter(dict):
        def __missing__(self, key): return f'{{{key}}}'

    # Format the template and then remove markdown for clean text
    formatted_text = template.format_map(SafeFormatter(replacements))
    clean_text = formatted_text.replace('**', '').replace('*', '')

    return clean_text