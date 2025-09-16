import os
from datetime import datetime
from typing import Dict, Any

def format_analysis_from_template(analysis_data: Dict[str, Any], symbol: str, timeframe: str) -> str:
    """
    Formats the analysis data into a human-readable report using a Markdown template.

    Args:
        analysis_data (Dict[str, Any]): The dictionary from FiboAnalyzer.
        symbol (str): The symbol being analyzed (e.g., 'BTC-USDT').
        timeframe (str): The timeframe being analyzed (e.g., '1D').

    Returns:
        str: A formatted string containing the full analysis report.
    """
    template_path = os.path.join('src', 'templates', 'analysis_template.md')

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        return "Error: Analysis template not found."

    now = datetime.now()

    # Helper to convert boolean to emoji
    def bool_to_emoji(value: bool) -> str:
        return "✅" if value else "❌"

    # Prepare data for formatting, providing default values for everything
    fib_levels = analysis_data.get('fib_levels', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})
    scenarios = analysis_data.get('scenarios', {})
    scenario1 = scenarios.get('scenario1', {})
    scenario2 = scenarios.get('scenario2', {})
    scenario3 = scenarios.get('scenario3', {})
    confirmations = analysis_data.get('confirmations', {})

    replacements = {
        "timeframe": timeframe,
        "symbol": symbol,
        "date": now.strftime('%Y/%m/%d'),
        "time": now.strftime('%H:%M:%S'),
        "current_price": f"{analysis_data.get('current_price', 0):.2f}",

        "swing_high": f"{swing_high.get('price', 0):.2f}",
        "swing_high_date": datetime.fromtimestamp(swing_high.get('timestamp', 0) / 1000).strftime('%Y/%m/%d'),
        "swing_low": f"{swing_low.get('price', 0):.2f}",
        "swing_low_date": datetime.fromtimestamp(swing_low.get('timestamp', 0) / 1000).strftime('%Y/%m/%d'),

        "fib_236": f"{fib_levels.get('fib_236', 0):.2f}",
        "fib_382": f"{fib_levels.get('fib_382', 0):.2f}",
        "fib_500": f"{fib_levels.get('fib_500', 0):.2f}",
        "fib_618": f"{fib_levels.get('fib_618', 0):.2f}",
        "fib_786": f"{fib_levels.get('fib_786', 0):.2f}",

        "fib_618_val": f"{fib_levels.get('fib_618', 0):.2f}",

        "confirmation_break_618": bool_to_emoji(confirmations.get('break_618', False)),
        "confirmation_daily_close": bool_to_emoji(confirmations.get('daily_close_above_fib', False)),
        "confirmation_volume": bool_to_emoji(confirmations.get('high_volume', False)),
        "confirmation_rsi": bool_to_emoji(confirmations.get('rsi_above_50', False)),
        "confirmation_reversal_candle": bool_to_emoji(confirmations.get('reversal_candle', False)),

        "pattern": analysis_data.get('pattern', 'N/A'),
        "pattern_confirm_hammer": bool_to_emoji(confirmations.get('is_hammer', False)),
        "pattern_confirm_engulfing": bool_to_emoji(confirmations.get('is_engulfing', False)),
        "pattern_confirm_break_doji": bool_to_emoji(confirmations.get('break_doji', False)),
        "pattern_confirm_close_above": bool_to_emoji(confirmations.get('close_above_doji', False)),
        "pattern_confirm_volume": bool_to_emoji(confirmations.get('volume_confirm_pattern', False)),

        "scenario1_title": scenario1.get('title', 'N/A'),
        "scenario1_prob": scenario1.get('prob', 0),
        "scenario1_target": f"{scenario1.get('target', 0):.2f}",
        "scenario1_entry": f"{scenario1.get('entry', 0):.2f}",
        "scenario1_stop_loss": f"{scenario1.get('stop_loss', 0):.2f}",

        "scenario2_title": scenario2.get('title', 'N/A'),
        "scenario2_prob": scenario2.get('prob', 0),
        "scenario2_target": f"{scenario2.get('target', 0):.2f}",
        "scenario2_entry": f"{scenario2.get('entry', 0):.2f}",
        "scenario2_stop_loss": f"{scenario2.get('stop_loss', 0):.2f}",

        "scenario3_title": scenario3.get('title', 'N/A'),
        "scenario3_prob": scenario3.get('prob', 0),
        "scenario3_target": f"{scenario3.get('target', 0):.2f}",
        "scenario3_entry": f"{scenario3.get('entry', 0):.2f}",
        "scenario3_stop_loss": f"{scenario3.get('stop_loss', 0):.2f}",

        "trade_title": analysis_data.get('trade_title', 'لا توجد إشارة قوية حالياً'),
        "trade_entry": analysis_data.get('trade_entry', 'N/A'),
        "trade_confirm_close": bool_to_emoji(confirmations.get('trade_close_4h', False)),
        "trade_confirm_volume": bool_to_emoji(confirmations.get('trade_volume_150', False)),
        "trade_confirm_macd": bool_to_emoji(confirmations.get('trade_macd_positive', False)),
        "trade_confirm_trendline": bool_to_emoji(confirmations.get('trade_trendline_break', False)),

        "trade_target1": analysis_data.get('trade_target1', 'N/A'),
        "trade_target2": analysis_data.get('trade_target2', 'N/A'),
        "trade_target3": analysis_data.get('trade_target3', 'N/A'),
        "trade_stop_loss": analysis_data.get('trade_stop_loss', 'N/A'),
    }

    # Use .format() to replace all placeholders
    formatted_text = template.format(**replacements)

    return formatted_text
