import os
from datetime import datetime
from typing import Dict, Any
from src.config import get_config

def format_dynamic_price(price: float) -> str:
    """Formats a price with a dynamic number of decimal places as a plain string."""
    if not isinstance(price, (int, float)) or price == 0: return 'N/A'
    if price > 10000: return f"{price:,.0f}"
    if price > 100: return f"{price:,.2f}"
    if price > 1: return f"{price:,.4f}"
    return f"{price:,.6f}"

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str, lang: str = "ar") -> str:
    """
    Formats the analysis data into a report using term-specific templates.
    """
    config = get_config()
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    # Determine which template to use
    term = 'long_term' # Default
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


    # Prepare data for the new template structure
    now = datetime.now()
    latest_data = analysis_data.get('latest_data', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    higher_tf_info = analysis_data.get('higher_tf_trend_info') or {}
    signal = analysis_data.get('signal', 'HOLD')
    fib_levels = analysis_data.get('fib_levels', {})

    # Interpretations
    adx_value = latest_data.get('adx', 0)
    adx_interpretation = "اتجاه قوي" if adx_value >= 25 else "اتجاه ضعيف أو عرضي"

    rsi_value = latest_data.get('rsi', 0)
    rsi_interpretation = "زخم إيجابي" if rsi_value > 50 else "زخم سلبي"
    if rsi_value > 70: rsi_interpretation = "تشبع شرائي"
    if rsi_value < 30: rsi_interpretation = "تشبع بيعي"

    macd_line = latest_data.get('macd', 0)
    macd_signal_line = latest_data.get('signal_line', 0)
    macd_histogram = latest_data.get('histogram', 0)
    macd_interpretation = "تقاطع إيجابي" if macd_line > macd_signal_line else "تقاطع سلبي"

    # Recommendation details
    summary_text = "لا توجد إشارة واضحة حاليًا. يوصى بالمراقبة."
    if analysis_data.get('final_reason'):
        reason_info = analysis_data.get('final_reason', {})
        reason_key = reason_info.get('key', 'N/A')
        summary_text = reason_key.replace('_', ' ').capitalize()


    if signal in ['BUY', 'SELL']:
        trade_recommendation = "شراء" if signal == 'BUY' else "بيع"
        entry_price = format_dynamic_price(scenario1.get('entry_zone', {}).get('best'))
        stop_loss = format_dynamic_price(scenario1.get('stop_loss'))
        targets = scenario1.get('targets', {})
        target_1 = format_dynamic_price(targets.get('tp1'))
        target_2 = format_dynamic_price(targets.get('tp2'))
        target_3 = format_dynamic_price(targets.get('tp3'))
    else:
        trade_recommendation = "انتظار / مراقبة"
        entry_price = "N/A"
        stop_loss = "N/A"
        target_1 = "N/A"
        target_2 = "N/A"
        target_3 = "N/A"

    stoch_k_val = latest_data.get('stoch_k', 0)
    stoch_d_val = latest_data.get('stoch_d', 0)
    stoch_interpretation = "N/A"
    if stoch_k_val > 80 and stoch_d_val > 80:
        stoch_interpretation = "تشبع شرائي"
    elif stoch_k_val < 20 and stoch_d_val < 20:
        stoch_interpretation = "تشبع بيعي"
    elif stoch_k_val > stoch_d_val:
        stoch_interpretation = "إشارة إيجابية"
    else:
        stoch_interpretation = "إشارة سلبية"

    volume_sma = latest_data.get('volume_sma', 0)
    current_volume = latest_data.get('volume', 0)
    volume_analysis_text = "N/A"
    if volume_sma > 0 and current_volume > 0:
        if current_volume > volume_sma * 1.5:
            volume_analysis_text = "حجم تداول مرتفع"
        elif current_volume < volume_sma * 0.5:
            volume_analysis_text = "حجم تداول منخفض"
        else:
            volume_analysis_text = "حجم تداول متوسط"

    # Fill the replacements dictionary
    replacements = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "current_price": format_dynamic_price(analysis_data.get('current_price')),
        "trend": str(analysis_data.get('trend', 'N/A')).upper(),
        "adx_value": f"{adx_value:.2f}",
        "adx_interpretation": adx_interpretation,
        "signal": signal,
        "summary": summary_text,
        "rsi_value": f"{rsi_value:.2f}",
        "rsi_interpretation": rsi_interpretation,
        "macd_line": f"{macd_line:.6f}",
        "macd_signal": f"{macd_signal_line:.6f}",
        "macd_histogram": f"{macd_histogram:.6f}",
        "macd_interpretation": macd_interpretation,
        "stoch_k": f"{stoch_k_val:.2f}",
        "stoch_d": f"{stoch_d_val:.2f}",
        "stoch_interpretation": stoch_interpretation,
        "swing_high": format_dynamic_price(swing_high.get('price')),
        "swing_low": format_dynamic_price(swing_low.get('price')),
        "fib_236": format_dynamic_price(fib_levels.get(0.236)),
        "fib_382": format_dynamic_price(fib_levels.get(0.382)),
        "fib_500": format_dynamic_price(fib_levels.get(0.5)),
        "fib_618": format_dynamic_price(fib_levels.get(0.618)),
        "fib_786": format_dynamic_price(fib_levels.get(0.786)),
        "volume_analysis": volume_analysis_text,
        "trade_recommendation": trade_recommendation,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "target_3": target_3,
        "notes": summary_text,
        "higher_tf": higher_tf_info.get('timeframe', 'N/A'),
        "higher_tf_trend": str(higher_tf_info.get('trend', 'N/A')).upper(),
    }

    class SafeFormatter(dict):
        def __missing__(self, key): return f'{{{key}}}'
    return template.format_map(SafeFormatter(replacements))