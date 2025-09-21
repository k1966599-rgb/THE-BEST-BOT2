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

    # --- Helpers for safe formatting ---
    def format_price(price):
        return f"${price:.2f}" if price and isinstance(price, (int, float)) and price > 0 else "غير متاح"

    def format_date(timestamp):
        if not timestamp or not isinstance(timestamp, (int, float)):
            return "غير متاح"
        # OKX timestamp is in milliseconds
        return datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')

    def format_bool(flag):
        return '✅' if flag else '❌'

    # --- Main Signal ---
    signal = analysis_data.get('signal', 'HOLD')
    signal_map = {'BUY': ('🟢', 'شراء'), 'SELL': ('🔴', 'بيع'), 'HOLD': ('🟡', 'محايد')}
    signal_emoji, signal_text = signal_map.get(signal, ('⚪️', 'غير محدد'))

    # --- Trend ---
    trend = analysis_data.get('trend', 'N/A')
    trend_emoji = '🔼' if trend == 'up' else '🔽'

    # --- Fibonacci Levels & Swings ---
    retracements = analysis_data.get('retracements', {})
    extensions = analysis_data.get('extensions', {})
    swing_high = analysis_data.get('swing_high', {})
    swing_low = analysis_data.get('swing_low', {})

    # --- Other data points ---
    scenarios = analysis_data.get('scenarios', {})
    confirmations = analysis_data.get('confirmations', {})

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

        "swing_high": format_price(swing_high.get('price')),
        "swing_high_date": format_date(swing_high.get('index')),
        "swing_low": format_price(swing_low.get('price')),
        "swing_low_date": format_date(swing_low.get('index')),

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

        # --- Now using the real confirmation data ---
        "confirmation_break_618": format_bool(confirmations.get('confirmation_break_618')),
        "confirmation_daily_close": "⚪️", # Still not implemented
        "fib_618_val": format_price(retracements.get('fib_618')),
        "confirmation_volume": format_bool(confirmations.get('confirmation_volume')),
        "confirmation_rsi": format_bool(confirmations.get('confirmation_rsi')),
        "confirmation_reversal_candle": format_bool(confirmations.get('confirmation_reversal_candle')),
        "pattern_confirm_hammer": "⚪️", # These pattern-specific confirms are not implemented yet
        "pattern_confirm_engulfing": "⚪️",
        "pattern_confirm_break_doji": "⚪️",
        "pattern_confirm_close_above": "⚪️",
        "pattern_confirm_volume": "⚪️",
        "scenario1_title": scenarios.get('scenario1', {}).get('title', 'N/A'),
        "scenario1_prob": scenarios.get('scenario1', {}).get('prob', 'N/A'),
        "scenario1_target": format_price(scenarios.get('scenario1', {}).get('target')),
        "scenario1_entry": format_price(scenarios.get('scenario1', {}).get('entry')),
        "scenario1_stop_loss": format_price(scenarios.get('scenario1', {}).get('stop_loss')),
        "scenario2_title": scenarios.get('scenario2', {}).get('title', 'N/A'),
        "scenario2_prob": scenarios.get('scenario2', {}).get('prob', 'N/A'),
        "scenario2_target": format_price(scenarios.get('scenario2', {}).get('target')),
        "scenario2_entry": format_price(scenarios.get('scenario2', {}).get('entry')),
        "scenario2_stop_loss": format_price(scenarios.get('scenario2', {}).get('stop_loss')),
        "scenario3_title": "غير محدد", "scenario3_prob": "N/A", "scenario3_target": "N/A",
        "scenario3_entry": "N/A", "scenario3_stop_loss": "N/A",
        "trade_title": "لا توجد صفقة مؤكدة حاليًا",
        "trade_entry": "N/A",
        "trade_confirm_close": "⚪️",
        "trade_confirm_volume": "⚪️",
        "trade_confirm_macd": "⚪️",
        "trade_confirm_trendline": "⚪️",
        "trade_target1": "N/A",
        "trade_target2": "N/A",
        "trade_target3": "N/A",
        "trade_stop_loss": "N/A",
    }

    # Using format_map with a custom dict to avoid crashing on any other missing keys
    class SafeFormatter(dict):
        def __missing__(self, key):
            return f'{{{key}}}'
    return template.format_map(SafeFormatter(replacements))
