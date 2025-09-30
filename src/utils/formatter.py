import os
from datetime import datetime
from typing import Dict, Any
from src.localization import get_text

def format_dynamic_price(price: float) -> str:
    """Formats a price with a dynamic number of decimal places as a plain string."""
    if not isinstance(price, (int, float)) or price == 0: return 'N/A'
    if price > 10000: return f"{price:,.0f}"
    if price > 100: return f"{price:,.2f}"
    if price > 1: return f"{price:,.4f}"
    return f"{price:,.6f}"

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str, lang: str = "ar") -> str:
    """Formats the analysis data into a professional, unified report using structured data."""
    # Handle cases where analysis is stopped early (e.g., no valid swings)
    if analysis_data.get('reason_key'):
        reason_text = get_text(analysis_data['reason_key'], lang)
        return f"📊 {symbol} | {timeframe}\n\n⚠️ {reason_text}"

    try:
        with open(os.path.join('src', 'templates', 'analysis_template.md'), 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return "Error: analysis_template.md not found."

    # --- 1. Prepare all data points and translations in one place ---
    now = datetime.now()
    signal = analysis_data.get('signal', 'HOLD')
    trend = analysis_data.get('trend', 'N/A')
    latest_data = analysis_data.get('latest_data', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    scenario2 = scenarios.get('scenario2', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    higher_tf_info = analysis_data.get('higher_tf_trend_info') or {}

    # --- Translations & Emojis ---
    signal_map = {'BUY': 'signal_buy', 'SELL': 'signal_sell', 'HOLD': 'signal_hold'}
    trend_map = {'up': ('🔼', get_text('trend_up', lang)), 'down': ('🔽', get_text('trend_down', lang))}
    signal_emoji_map = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}

    signal_name = get_text(signal_map.get(signal, 'signal_hold'), lang)
    signal_emoji = signal_emoji_map.get(signal, '⚪️')
    trend_emoji, trend_name = trend_map.get(trend, ('↔️', get_text('trend_sideways', lang)))

    # Handle MTA trend translation carefully, defaulting to sideways if not present
    mta_trend_key = f"trend_{higher_tf_info.get('trend', 'sideways')}"
    mta_trend_name = get_text(mta_trend_key, lang)
    mta_emoji = trend_map.get(higher_tf_info.get('trend', 'sideways'), ('↔️', ''))[0]
    mta_compatibility = get_text('compatible', lang) if trend == higher_tf_info.get('trend') and higher_tf_info.get('trend') else ""

    # --- Build Plan Section from structured data ---
    plan_section = ""
    if signal in ['BUY', 'SELL']:
        entry_zone = scenario1.get('entry_zone', {})
        targets = scenario1.get('targets', {})
        # The trade logic is now the final_reason
        trade_logic_key_info = analysis_data.get('final_reason', {})
        trade_logic_text = get_text(trade_logic_key_info.get('key'), lang).format(**trade_logic_key_info.get('context', {}))

        plan_section = (
            f"### **2. {get_text('section_trade_plan_title', lang)}**\n"
            f"*   **{get_text('trade_logic', lang)}:** {trade_logic_text}\n"
            f"*   **{get_text('entry_zone', lang)}:** {format_dynamic_price(entry_zone.get('start'))} - {format_dynamic_price(entry_zone.get('end'))}\n"
            f"*   **{get_text('best_entry', lang)}:** ~{format_dynamic_price(entry_zone.get('best'))}\n"
            f"*   **{get_text('stop_loss', lang)}:** {format_dynamic_price(scenario1.get('stop_loss'))}\n"
            f"*   **{get_text('targets', lang)}:**\n" +
            "\n".join([f"    *   TP{i+1}: {format_dynamic_price(t)}" for i, t in enumerate(targets.values()) if t]) +
            f"\n*   **{get_text('trade_risk_assessment', lang)}:**\n"
            f"    *   {get_text('risk_to_reward', lang)}: {analysis_data.get('rr_ratio', 0.0):.2f}:1\n"
            f"    *   {get_text('confidence', lang)}: {analysis_data.get('confidence', 0)}%"
        )
    else: # HOLD
        # Use the final_reason as the main conclusion for monitoring
        conclusion_key_info = analysis_data.get('final_reason', {})
        conclusion_text_monitoring = get_text(conclusion_key_info.get('key'), lang).format(**conclusion_key_info.get('context', {}))

        # Scenario 1 (usually bullish)
        bullish_scenario_title = get_text(scenario1.get('title_key', ''), lang)
        bullish_activation = get_text('monitoring_activation_condition', lang).format(level=format_dynamic_price(swing_high.get('price')))
        bullish_target_text = format_dynamic_price(scenario1.get('targets', {}).get('tp1')) or "N/A"

        # Scenario 2 (usually bearish)
        bearish_scenario_title = get_text(scenario2.get('title_key', ''), lang)
        bearish_activation = get_text('monitoring_activation_condition', lang).format(level=format_dynamic_price(swing_low.get('price')))
        bearish_target_text = format_dynamic_price(scenario2.get('target')) or "N/A"

        plan_section = (
            f"### **2. {get_text('section_monitoring_plan_title', lang)}**\n"
            f"*   **{get_text('monitoring_conclusion', lang)}:** {conclusion_text_monitoring}\n"
            f"*   **{bullish_scenario_title}:**\n"
            f"    *   {get_text('monitoring_activation_condition', lang)}: {bullish_activation}\n"
            f"    *   {get_text('monitoring_expected_targets', lang)}: {bullish_target_text}\n"
            f"*   **{bearish_scenario_title}:**\n"
            f"    *   {get_text('monitoring_activation_condition', lang)}: {bearish_activation}\n"
            f"    *   {get_text('monitoring_expected_targets', lang)}: {bearish_target_text}"
        )

    # --- Process Final Reason and Reasons List ---
    final_reason_info = analysis_data.get('final_reason', {})
    # Translate the final reason, providing an empty dict for context if missing
    conclusion_text = get_text(final_reason_info.get('key', ''), lang).format(**final_reason_info.get('context', {}))

    reasons_list = analysis_data.get('reasons', [])
    # Translate each reason from the structured list
    translated_reasons = [
        get_text(r.get('key'), lang).format(**r.get('context', {})) for r in reasons_list
    ]
    reasons_text = "\n".join([f"*   ✔️ {reason}" for reason in translated_reasons]) if translated_reasons else f"*   - {get_text('details_no_strength_reasons', lang)}"

    # --- Other Details ---
    key_level_text = f"{format_dynamic_price(scenario1.get('entry_zone', {}).get('start'))} - {format_dynamic_price(scenario1.get('entry_zone', {}).get('end'))}" if signal in ['BUY', 'SELL'] else f"{format_dynamic_price(swing_high.get('price'))} / {format_dynamic_price(swing_low.get('price'))}"

    adx_value = latest_data.get('adx', 0.0)
    adx_text = get_text('strong_trend', lang) if adx_value >= 25 else ""
    rsi_value = latest_data.get('rsi', 0.0)
    rsi_text = get_text('positive_momentum' if rsi_value > 50 else 'negative_momentum', lang)
    macd_text = get_text('macd_positive' if latest_data.get('macd', 0) > latest_data.get('signal_line', 0) else 'macd_negative', lang)

    cancellation_text = get_text('details_cancellation_condition', lang).format(signal_type=signal_name, stop_loss=format_dynamic_price(scenario1.get('stop_loss', 0)))

    key_levels = analysis_data.get('key_levels', [])
    current_price = analysis_data.get('current_price', 0)
    resistance_levels = " | ".join([format_dynamic_price(lvl['level']) for lvl in key_levels if lvl['level'] > current_price] or ["N/A"])
    support_levels = " | ".join([format_dynamic_price(lvl['level']) for lvl in key_levels if lvl['level'] <= current_price] or ["N/A"])

    # --- 2. Create the final, unified replacements dictionary ---
    replacements = {
        "report_title_text": get_text('report_title', lang).format(symbol=symbol, timeframe=timeframe),
        "report_updated_at_text": get_text('report_updated_at', lang).format(date=now.strftime('%Y-%m-%d'), time=now.strftime('%H:%M')),
        "summary_title_text": get_text('section_summary_title', lang),
        "summary_signal_text": get_text('summary_signal', lang),
        "signal_emoji": signal_emoji, "signal_name": signal_name,
        "summary_conclusion_text": get_text('summary_conclusion', lang),
        "conclusion_text": conclusion_text,
        "summary_key_level_text": get_text('summary_key_level', lang),
        "key_level_text": key_level_text,
        "plan_section": plan_section,
        "details_title_text": get_text('section_analysis_details_title', lang),
        "details_market_structure_text": get_text('details_market_structure', lang),
        "details_current_trend_text": get_text('details_current_trend', lang).format(timeframe=timeframe),
        "trend_emoji": trend_emoji, "trend_name": trend_name,
        "details_general_trend_text": get_text('details_general_trend', lang).format(timeframe_parent=higher_tf_info.get('timeframe', 'N/A')),
        "mta_emoji": mta_emoji, "mta_trend_name": mta_trend_name, "mta_compatibility": mta_compatibility,
        "details_swing_high_text": get_text('details_swing_high', lang), "swing_high_price": format_dynamic_price(swing_high.get('price')),
        "details_swing_low_text": get_text('details_swing_low', lang), "swing_low_price": format_dynamic_price(swing_low.get('price')),
        "details_indicators_reading_text": get_text('details_indicators_reading', lang),
        "details_trend_strength_text": get_text('details_trend_strength', lang), "adx_value": f"{adx_value:.2f}", "adx_text": adx_text,
        "details_momentum_text": get_text('details_momentum', lang), "rsi_value": f"{rsi_value:.2f}", "rsi_text": rsi_text,
        "details_macd_text": get_text('details_macd', lang), "macd_text": macd_text,
        "details_confirmation_score_text": get_text('details_confirmation_score', lang),
        "score_value": analysis_data.get('score', 0), "score_max": sum(analysis_data.get('weights', {}).values()) or 9,
        "reasons_text": reasons_text,
        "details_alternative_scenario_text": get_text('details_alternative_scenario', lang),
        "cancellation_text": cancellation_text,
        "sr_title_text": get_text('section_support_resistance_title', lang),
        "sr_resistance_text": get_text('sr_resistance', lang), "resistance_levels": resistance_levels,
        "sr_support_text": get_text('sr_support', lang), "support_levels": support_levels,
        "disclaimer_text": get_text('disclaimer', lang),
    }

    # --- 3. Format the template ---
    class SafeFormatter(dict):
        def __missing__(self, key): return f'{{{key}}}'
    return template.format_map(SafeFormatter(replacements))