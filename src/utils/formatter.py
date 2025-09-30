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
    Formats the analysis data into a report using the 'Enhanced Professional' template,
    with smart logic for summary and dynamic sections.
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
    now = datetime.now()
    latest_data = analysis_data.get('latest_data', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    higher_tf_info = analysis_data.get('higher_tf_trend_info') or {}
    signal = analysis_data.get('signal', 'HOLD')
    retracements = analysis_data.get('retracements', {})
    final_reason = analysis_data.get('final_reason')

    # --- Smart Summary Interpretation ---
    summary_text = "لا توجد إشارة واضحة حاليًا. يوصى بالمراقبة."
    if final_reason and isinstance(final_reason, dict):
        reason_key = final_reason.get('key')
        # Translate technical reasons into user-friendly summaries
        if reason_key == 'final_reason_signal_confirmed':
            summary_text = f"إشارة {signal.lower()} قوية مدعومة بتوافق المؤشرات الفنية."
        elif reason_key == 'final_reason_score_met_adx_weak':
            summary_text = f"إشارة {signal.lower()} محتملة، لكن قوة الاتجاه ضعيفة. يوصى بالحذر."
        elif reason_key == 'final_reason_mta_override':
            original_signal = final_reason.get('context', {}).get('original_signal', 'N/A')
            summary_text = f"تم إلغاء إشارة {original_signal} بسبب تعارضها مع اتجاه الإطار الزمني الأعلى."
        # Default for 'final_reason_score_not_met' remains the default summary_text

    # --- Technical Indicator Interpretation ---
    adx_value = latest_data.get('adx', 0)
    adx_interpretation = "قوي" if adx_value >= 25 else "ضعيف أو عرضي"

    rsi_value = latest_data.get('rsi', 0)
    rsi_interpretation = "زخم إيجابي" if rsi_value > 50 else "زخم سلبي"
    if rsi_value > 70: rsi_interpretation = "تشبع شرائي"
    if rsi_value < 30: rsi_interpretation = "تشبع بيعي"

    macd_line = latest_data.get('macd', 0)
    macd_signal_line = latest_data.get('signal_line', 0)
    macd_interpretation = "تقاطع إيجابي" if macd_line > macd_signal_line else "تقاطع سلبي"

    stoch_k_val = latest_data.get('stoch_k', 0)
    stoch_d_val = latest_data.get('stoch_d', 0)
    stoch_interpretation = "محايد"
    if stoch_k_val > 80 and stoch_d_val > 80: stoch_interpretation = "تشبع شرائي"
    elif stoch_k_val < 20 and stoch_d_val < 20: stoch_interpretation = "تشبع بيعي"
    elif stoch_k_val > stoch_d_val: stoch_interpretation = "إشارة إيجابية"
    else: stoch_interpretation = "إشارة سلبية"

    volume_sma = latest_data.get('volume_sma', 0)
    current_volume = latest_data.get('volume', 0)
    volume_analysis_text = "متوسط"
    if volume_sma > 0 and current_volume > 0:
        if current_volume > volume_sma * 1.5: volume_analysis_text = "مرتفع"
        elif current_volume < volume_sma * 0.5: volume_analysis_text = "منخفض"

    # --- Dynamic Sections ---
    # Build additional confirmations section only with available data
    confirmations = [
        "**تأكيدات إضافية**",
        f"*   **قوة الاتجاه (ADX):** {adx_value:.2f} ({adx_interpretation})",
        f"*   **نمط الشموع:** {analysis_data.get('pattern', 'لا يوجد')}"
    ]
    if higher_tf_info.get('timeframe'):
        confirmations.append(f"*   **اتجاه الفريم الأعلى ({higher_tf_info['timeframe']}):** {str(higher_tf_info.get('trend', 'N/A')).upper()}")
    additional_confirmations_section = "\n".join(confirmations)

    # Build trade recommendation section only for BUY/SELL signals
    trade_recommendation_section = ""
    if signal in ['BUY', 'SELL']:
        entry_price = format_dynamic_price(scenario1.get('entry_zone', {}).get('best'))
        stop_loss = format_dynamic_price(scenario1.get('stop_loss'))
        targets = scenario1.get('targets', {})
        target_1 = format_dynamic_price(targets.get('tp1'))
        target_2 = format_dynamic_price(targets.get('tp2'))

        recommendation_lines = [
            "**توصية التداول**",
            f"*   **الدخول:** {entry_price}",
            f"*   **وقف الخسارة:** {stop_loss}",
            f"*   **الهدف 1:** {target_1}",
            f"*   **الهدف 2:** {target_2}"
        ]
        trade_recommendation_section = "\n".join(recommendation_lines)

    # --- Final Replacements Dictionary ---
    replacements = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "trend": str(analysis_data.get('trend', 'N/A')).upper(),
        "signal": signal,
        "confidence_score": f"{analysis_data.get('confidence', 50):.0f}",
        "summary": summary_text,
        "rsi_value": f"{rsi_value:.2f}",
        "rsi_interpretation": rsi_interpretation,
        "macd_interpretation": macd_interpretation,
        "stoch_interpretation": stoch_interpretation,
        "volume_analysis": volume_analysis_text,
        "additional_confirmations_section": additional_confirmations_section,
        "swing_high": format_dynamic_price(swing_high.get('price')),
        "swing_low": format_dynamic_price(swing_low.get('price')),
        "fib_382": format_dynamic_price(retracements.get('fib_382')),
        "fib_500": format_dynamic_price(retracements.get('fib_500')),
        "fib_618": format_dynamic_price(retracements.get('fib_618')),
        "trade_recommendation_section": trade_recommendation_section,
    }

    class SafeFormatter(dict):
        def __missing__(self, key): return f'{{{key}}}'
    return template.format_map(SafeFormatter(replacements))