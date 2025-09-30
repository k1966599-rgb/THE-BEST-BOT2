import pytest
from src.utils.formatter import format_analysis_from_template

# Fixtures provide mock data for different scenarios.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal using the new structured format."""
    return {
        "signal": "BUY",
        "final_reason": {'key': 'final_reason_signal_confirmed', 'context': {'score': 8, 'trend': 'up'}},
        "scenarios": {
            "scenario1": {
                "entry_zone": {"best": 64800},
                "stop_loss": 63900,
                "targets": {"tp1": 67100, "tp2": 68500, "tp3": 70000}
            }
        },
        "trend": "up",
        "higher_tf_trend_info": {"trend": "up", "timeframe": "1D"},
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0, "histogram": 1},
        "current_price": 66100,
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
        "fib_levels": {0.618: 65000}
    }

@pytest.fixture
def mock_hold_analysis_data():
    """Provides a mock analysis_data dictionary for a HOLD signal using the new structured format."""
    return {
        "signal": "HOLD",
        "final_reason": {'key': 'final_reason_score_not_met', 'context': {'score': 3, 'threshold': 5}},
        "scenarios": {"scenario1": {}, "scenario2": {}},
        "trend": "sideways",
        "higher_tf_trend_info": None,
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1, "histogram": 0},
        "current_price": 66000,
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
        "fib_levels": {}
    }

def test_format_buy_signal_report_is_correct_and_complete(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates a complete Arabic report for a BUY signal
    using the new templates, with no leftover placeholders.
    """
    # Testing with '4H' which falls under 'long_term'
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H")

    # --- Assertions for BUY signal ---
    assert "**التحليل الفني لـ BTC/USDT على فريم 4H (طويل المدى)**" in report
    assert "**الإشارة الحالية:** **BUY**" in report
    assert "**نوع العملية:** شراء" in report
    assert "**سعر الدخول المقترح:** 64,800" in report
    assert "**وقف الخسارة (Stop-Loss):** 63,900" in report
    assert "الهدف الأول: 67,100" in report
    # Check that no placeholders are left
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_format_hold_signal_report_is_correct_and_complete(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates a complete Arabic report for a HOLD signal
    using the new templates, with no leftover placeholders.
    """
    # Testing with '15m' which falls under 'medium_term'
    report = format_analysis_from_template(mock_hold_analysis_data, "ETH/USDT", "15m")

    # --- Assertions for HOLD signal ---
    assert "**التحليل الفني لـ ETH/USDT على فريم 15m (متوسط المدى)**" in report
    assert "**الإشارة الحالية:** **HOLD**" in report
    assert "**نوع العملية:** انتظار / مراقبة" in report
    assert "**سعر الدخول المقترح:** N/A" in report
    assert "**وقف الخسارة (Stop-Loss):** N/A" in report
    # Check that no placeholders are left
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_formatter_selects_short_term_template_correctly(mock_buy_analysis_data):
    """
    Tests that the formatter selects the short-term template for a short-term timeframe.
    """
    # Testing with '5m' which falls under 'short_term'
    report = format_analysis_from_template(mock_buy_analysis_data, "SOL/USDT", "5m")
    assert "**التحليل الفني لـ SOL/USDT على فريم 5m (قصير المدى)**" in report
    assert '{' not in report
    assert '}' not in report