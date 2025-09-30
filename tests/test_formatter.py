import pytest
from src.utils.formatter import format_analysis_from_template

# Fixtures provide mock data for different scenarios.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal using the new structured format."""
    return {
        "signal": "BUY",
        "confidence": 85.0,
        "final_reason": {'key': 'final_reason_signal_confirmed', 'context': {'score': 8, 'trend': 'up'}},
        "scenarios": {
            "scenario1": {
                "entry_zone": {"best": 64800},
                "stop_loss": 63900,
                "targets": {"tp1": 67100, "tp2": 68500}
            }
        },
        "trend": "up",
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0, "histogram": 1, "stoch_k": 60, "stoch_d": 55, "volume": 120, "volume_sma": 100},
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
        "confidence": 40.0,
        "final_reason": {'key': 'final_reason_score_not_met', 'context': {'score': 3, 'threshold': 5}},
        "scenarios": {"scenario1": {}, "scenario2": {}},
        "trend": "sideways",
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1, "histogram": 0, "stoch_k": 50, "stoch_d": 52, "volume": 80, "volume_sma": 100},
        "current_price": 66000,
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
        "fib_levels": {0.618: 65000}
    }

def test_format_buy_signal_report_is_correct_and_complete(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates a complete Arabic report for a BUY signal
    using the new "Balanced Professional" template.
    """
    # Testing with '4H' which falls under 'long_term'
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H")

    # --- Assertions for BUY signal ---
    assert "**تحليل BTC/USDT | الإطار الزمني: 4H (طويل المدى)**" in report
    assert "**الإشارة:** **BUY**" in report
    assert "**الثقة:** 85%" in report
    # Check that the recommendation section is present
    assert "**توصية التداول**" in report
    assert "**الدخول:** 64,800" in report
    assert "**وقف الخسارة:** 63,900" in report
    assert "**الهدف 1:** 67,100" in report
    # Check that no placeholders are left
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_format_hold_signal_report_is_correct_and_complete(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates a report for a HOLD signal and
    hides the trade recommendation section.
    """
    # Testing with '30m' which falls under 'medium_term'
    report = format_analysis_from_template(mock_hold_analysis_data, "ETH/USDT", "30m")

    # --- Assertions for HOLD signal ---
    assert "**تحليل ETH/USDT | الإطار الزمني: 30m (متوسط المدى)**" in report
    assert "**الإشارة:** **HOLD**" in report
    # Check that the recommendation section is NOT present
    assert "**توصية التداول**" not in report
    assert "**الدخول:**" not in report
    # Check that no placeholders are left
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_formatter_selects_short_term_template_correctly(mock_buy_analysis_data):
    """
    Tests that the formatter selects the short-term template for a short-term timeframe.
    """
    # Testing with '5m' which falls under 'short_term'
    report = format_analysis_from_template(mock_buy_analysis_data, "SOL/USDT", "5m")
    assert "**تحليل SOL/USDT | الإطار الزمني: 5m (قصير المدى)**" in report
    assert '{' not in report
    assert '}' not in report