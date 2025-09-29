import os
from datetime import datetime
from typing import Dict, Any
from ..localization import get_text

def format_dynamic_price(price: float) -> str:
    """Formats a price with a dynamic number of decimal places as a plain string."""
    if not isinstance(price, (int, float)) or price == 0:
        return 'N/A'
    if price > 10000: return f"{price:,.0f}"
    if price > 100: return f"{price:,.2f}"
    if price > 1: return f"{price:,.4f}"
    return f"{price:,.6f}"

def _build_trade_plan_section(analysis_data: Dict[str, Any], lang: str) -> str:
    """Builds the detailed trade plan for BUY/SELL signals."""
    scenario1 = analysis_data.get('scenarios', {}).get('scenario1', {})
    entry_zone = scenario1.get('entry_zone', {})
    targets = scenario1.get('targets', {})

    entry_zone_text = f"**{format_dynamic_price(entry_zone.get('start'))} - {format_dynamic_price(entry_zone.get('end'))}**"
    targets_text = "\n".join([f"    - TP{i+1}: **{format_dynamic_price(t)}**" for i, t in enumerate(targets.values()) if t])
    rr_ratio_text = f"**{analysis_data.get('rr_ratio', 0.0):.2f}:1**"
    confidence_text = f"**{analysis_data.get('confidence', 0)}%**"

    fibo_trend = analysis_data.get('fibo_trend', 'up')
    trend_text = get_text('trend_up' if fibo_trend == 'up' else 'trend_down', lang)
    trade_logic_text = f"الدخول مع الاتجاه {trend_text} العام بعد تصحيح السعر إلى منطقة الطلب المحددة بمستويات فيبوناتشي."
    if lang == 'en':
        trade_logic_text = f"Entering with the general {trend_text} trend after a price correction to the demand zone defined by Fibonacci levels."

    return (
        f"{get_text('section_trade_plan_title', lang)}\n"
        f"- **{get_text('trade_logic', lang)}:** {trade_logic_text}\n"
        f"- **{get_text('entry_zone', lang)}:** {entry_zone_text}\n"
        f"- **{get_text('best_entry', lang)}:** **~{format_dynamic_price(entry_zone.get('best'))}**\n"
        f"- **{get_text('stop_loss', lang)}:** **{format_dynamic_price(scenario1.get('stop_loss'))}**\n"
        f"- **{get_text('targets', lang)}:**\n{targets_text}\n"
        f"- **{get_text('trade_risk_assessment', lang)}:**\n"
        f"  - {get_text('risk_to_reward', lang)}: {rr_ratio_text}\n"
        f"  - {get_text('confidence', lang)}: {confidence_text}"
    )

def _build_monitoring_plan_section(analysis_data: Dict[str, Any], lang: str) -> str:
    """Builds the monitoring plan for HOLD signals."""
    swing_high_price = format_dynamic_price(analysis_data.get('swing_high', {}).get('price'))
    swing_low_price = format_dynamic_price(analysis_data.get('swing_low', {}).get('price'))

    bullish_targets = analysis_data.get('scenarios', {}).get('scenario1', {}).get('targets', {})
    bearish_target = analysis_data.get('scenarios', {}).get('scenario2', {}).get('target')

    conclusion_text = "السوق في حالة تذبذب عرضي، مما يتطلب انتظار إشارة تأكيد واضحة."
    if lang == 'en':
        conclusion_text = "The market is in a sideways consolidation, requiring a clear confirmation signal."

    bullish_activation = f"إغلاق شمعة 4 ساعات فوق مستوى المقاومة **{swing_high_price}**"
    if lang == 'en':
        bullish_activation = f"A 4-hour candle close above the resistance level of **{swing_high_price}**"

    bearish_activation = f"إغلاق شمعة 4 ساعات أسفل مستوى الدعم **{swing_low_price}**"
    if lang == 'en':
        bearish_activation = f"A 4-hour candle close below the support level of **{swing_low_price}**"

    return (
        f"{get_text('section_monitoring_plan_title', lang)}\n"
        f"- **{get_text('monitoring_conclusion', lang)}:** {conclusion_text}\n"
        f"- **{get_text('monitoring_bullish_scenario', lang)}:**\n"
        f"  - {get_text('monitoring_activation_condition', lang)}: {bullish_activation}\n"
        f"  - {get_text('monitoring_expected_targets', lang)}: **{format_dynamic_price(bullish_targets.get('tp1'))}**\n"
        f"- **{get_text('monitoring_bearish_scenario', lang)}:**\n"
        f"  - {get_text('monitoring_activation_condition', lang)}: {bearish_activation}\n"
        f"  - {get_text('monitoring_expected_targets', lang)}: **{format_dynamic_price(bearish_target)}**"
    )

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str, lang: str = "ar") -> str:
    """Formats the analysis data into a professional report using a template."""
    if analysis_data.get('reason'):
        return f"📊 تحليل {symbol} | {timeframe}\n\n⚠️ تم إيقاف التحليل.\nالسبب: {analysis_data['reason']}"

    try:
        with open(os.path.join('src', 'templates', 'analysis_template.md'), 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return "Error: analysis_template.md not found."

    now = datetime.now()
    signal = analysis_data.get('signal', 'HOLD')
    trend = analysis_data.get('trend', 'N/A')

    # --- Translations & Emojis ---
    signal_map = {'BUY': 'signal_buy', 'SELL': 'signal_sell', 'HOLD': 'signal_hold'}
    trend_map = {'up': ('🔼', get_text('trend_up', lang)), 'down': ('🔽', get_text('trend_down', lang))}
    signal_emoji_map = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}

    signal_text = get_text(signal_map.get(signal, 'signal_hold'), lang)
    signal_emoji = signal_emoji_map.get(signal, '⚪️')
    trend_emoji, trend_text_val = trend_map.get(trend, ('↔️', get_text('trend_sideways', lang)))

    # --- Section 1: Executive Summary ---
    conclusion_text = analysis_data.get('final_reason', '')
    key_level_text = ""
    if signal in ['BUY', 'SELL']:
        entry_zone = analysis_data.get('scenarios', {}).get('scenario1', {}).get('entry_zone', {})
        key_level_text = f"**{format_dynamic_price(entry_zone.get('start'))} - {format_dynamic_price(entry_zone.get('end'))}**"
    else:
        key_level_text = f"**{format_dynamic_price(analysis_data.get('swing_high', {}).get('price'))} / {format_dynamic_price(analysis_data.get('swing_low', {}).get('price'))}**"

    # --- Section 2: Plan ---
    trade_plan_section = _build_trade_plan_section(analysis_data, lang) if signal in ['BUY', 'SELL'] else _build_monitoring_plan_section(analysis_data, lang)

    # --- Section 3: Details ---
    latest_data = analysis_data.get('latest_data', {})
    higher_tf_info = analysis_data.get('higher_tf_trend_info')
    mta_text, mta_emoji, mta_compatibility = get_text('trend_sideways', lang), '↔️', ''
    if higher_tf_info:
        higher_tf_trend = higher_tf_info.get('trend', 'N/A')
        mta_emoji, mta_text = trend_map.get(higher_tf_trend, ('↔️', get_text('trend_sideways', lang)))
        if (trend == 'up' and higher_tf_trend == 'up') or (trend == 'down' and higher_tf_trend == 'down'):
            mta_compatibility = get_text('compatible', lang)

    adx_value = latest_data.get('adx', 0.0)
    adx_text = get_text('strong_trend', lang) if adx_value >= 25 else ""
    rsi_value = latest_data.get('rsi', 0.0)
    rsi_text = get_text('positive_momentum', lang) if rsi_value > 50 else get_text('negative_momentum', lang)
    macd_text = get_text('macd_positive', lang) if latest_data.get('macd', 0) > latest_data.get('signal_line', 0) else get_text('macd_negative', lang)
    reasons_list = analysis_data.get('reasons', [])
    if reasons_list:
        reasons_text = "\n".join([f"  - ✔️ {reason}" for reason in reasons_list])
    else:
        reasons_text = f"  - {get_text('details_no_strength_reasons', lang)}"

    cancellation_text = get_text('details_cancellation_condition', lang).format(
        signal_type=signal_text.lower(),
        stop_loss=format_dynamic_price(analysis_data.get('scenarios',{}).get('scenario1',{}).get('stop_loss', 0))
    )

    # --- Section 4: S/R Levels ---
    key_levels = analysis_data.get('key_levels', [])
    resistance_levels = sorted([lvl['level'] for lvl in key_levels if lvl['level'] > analysis_data.get('current_price', 0)], reverse=False)
    support_levels = sorted([lvl['level'] for lvl in key_levels if lvl['level'] <= analysis_data.get('current_price', 0)], reverse=True)

    replacements = {
        # Titles and Meta
        "report_title": get_text('report_title', lang).format(symbol=symbol, timeframe=timeframe),
        "report_updated_at": get_text('report_updated_at', lang).format(date=now.strftime('%Y-%m-%d'), time=now.strftime('%H:%M')),
        "disclaimer": get_text('disclaimer', lang),
        # Section 1
        "section_summary_title": get_text('section_summary_title', lang),
        "summary_signal": get_text('summary_signal', lang),
        "signal_emoji": signal_emoji, "signal_text": signal_text,
        "summary_conclusion": get_text('summary_conclusion', lang),
        "conclusion_text": conclusion_text,
        "summary_key_level": get_text('summary_key_level', lang),
        "key_level_text": key_level_text,
        # Section 2
        "trade_plan_section": trade_plan_section,
        # Section 3
        "section_analysis_details_title": get_text('section_analysis_details_title', lang),
        "details_market_structure": get_text('details_market_structure', lang),
        "details_current_trend": get_text('details_current_trend', lang).format(timeframe=timeframe),
        "trend_emoji": trend_emoji, "trend_text": trend_text_val,
        "details_general_trend": get_text('details_general_trend', lang).format(timeframe_parent=higher_tf_info.get('timeframe', 'N/A') if higher_tf_info else 'N/A'),
        "mta_emoji": mta_emoji, "mta_text": mta_text, "mta_compatibility": mta_compatibility,
        "details_swing_high": get_text('details_swing_high', lang),
        "swing_high_price": format_dynamic_price(analysis_data.get('swing_high', {}).get('price')),
        "details_swing_low": get_text('details_swing_low', lang),
        "swing_low_price": format_dynamic_price(analysis_data.get('swing_low', {}).get('price')),
        "details_indicators_reading": get_text('details_indicators_reading', lang),
        "details_trend_strength": get_text('details_trend_strength', lang),
        "adx_value": f"{adx_value:.2f}", "adx_text": adx_text,
        "details_momentum": get_text('details_momentum', lang),
        "rsi_value": f"{rsi_value:.2f}", "rsi_text": rsi_text,
        "details_macd": get_text('details_macd', lang), "macd_text": macd_text,
        "details_confirmation_score": get_text('details_confirmation_score', lang),
        "score_value": analysis_data.get('score', 0), "score_max": sum(analysis_data.get('weights', {}).values()) or 9,
        "reasons_text": reasons_text,
        "details_alternative_scenario": get_text('details_alternative_scenario', lang),
        "cancellation_text": cancellation_text,
        # Section 4
        "section_support_resistance_title": get_text('section_support_resistance_title', lang),
        "sr_resistance": get_text('sr_resistance', lang),
        "resistance_levels": " | ".join([format_dynamic_price(p) for p in resistance_levels]) or "N/A",
        "sr_support": get_text('sr_support', lang),
        "support_levels": " | ".join([format_dynamic_price(p) for p in support_levels]) or "N/A",
    }

    class SafeFormatter(dict):
        def __missing__(self, key): return f'{{{key}}}'
    return template.format_map(SafeFormatter(replacements))