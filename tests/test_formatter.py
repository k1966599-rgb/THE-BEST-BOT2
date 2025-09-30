import pytest
from src.utils.formatter import format_analysis_from_template

# Fixtures provide mock data that closely resembles the output of FiboAnalyzer.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a realistic mock analysis_data for a BUY signal."""
    return {
        "signal": "BUY", "confidence": 85.0,
        "final_reason": {'key': 'final_reason_signal_confirmed'},
        "scenarios": {"scenario1": {"entry_zone": {"best": 64800}, "stop_loss": 63900, "targets": {"tp1": 67100, "tp2": 68500}}},
        "trend": "up",
        "latest_data": {"adx": 28.5},
        "key_support": {'level': 65000, 'type': 'فيبوناتشي 0.618'},
        "key_resistance": {'level': 68000, 'type': 'قمة سابقة'},
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
        "retracements": {"fib_382": 64000, "fib_500": 64500, "fib_618": 65000, "trend": "up"}
    }

@pytest.fixture
def mock_hold_analysis_data():
    """Provides a realistic mock analysis_data for a HOLD signal."""
    return {
        "signal": "HOLD", "confidence": 40.0,
        "final_reason": {'key': 'final_reason_score_not_met'},
        "scenarios": {"scenario1": {}},
        "trend": "sideways",
        "latest_data": {"adx": 18.0},
        "key_support": {'level': 63000, 'type': 'قاع سابق'},
        "key_resistance": {'level': 64000, 'type': 'فيبوناتشي 0.382'},
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
        "retracements": {"fib_382": 64000, "fib_500": 64500, "fib_618": 65000, "trend": "down"}
    }

def test_format_buy_signal_report_is_clean_and_correct(mock_buy_analysis_data):
    """
    Tests that a BUY signal report is correctly formatted with the clean text template
    and includes the trade recommendation.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H")

    # --- Assertions for BUY signal ---
    assert "تحليل شامل وقرار تداول: BTC/USDT | 4H (طويل المدى)" in report
    assert "النوع:           BUY" in report
    assert "أهم دعم:        65,000 (فيبوناتشي 0.618)" in report
    assert "مستوى 1 (قمة):    68,000" in report
    assert "مستوى 0 (قاع):     63,000" in report
    # Check that the recommendation section is present and clean
    assert "--- صفقة مقترحة ---" in report
    assert "الدخول:         64,800" in report
    # Check that no markdown characters are left
    assert '*' not in report
    assert '#' not in report
    assert '{' not in report and '}' not in report

def test_format_hold_signal_report_is_clean_and_hides_trade_section(mock_hold_analysis_data):
    """
    Tests that a HOLD signal report is clean and completely hides the trade recommendation section.
    """
    report = format_analysis_from_template(mock_hold_analysis_data, "ETH/USDT", "1D")

    # --- Assertions for HOLD signal ---
    assert "تحليل شامل وقرار تداول: ETH/USDT | 1D (طويل المدى)" in report
    assert "النوع:           HOLD" in report
    assert "أهم دعم:        63,000 (قاع سابق)" in report
    # Check that the recommendation section is NOT present
    assert "--- صفقة مقترحة ---" not in report
    # Check that no markdown characters are left
    assert '*' not in report
    assert '#' not in report
    assert '{' not in report and '}' not in report

def test_formatter_selects_short_term_template_correctly(mock_buy_analysis_data):
    """
    Tests that the formatter selects the short-term template for a short-term timeframe.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "SOL/USDT", "5m")
    assert "تحليل شامل وقرار تداول: SOL/USDT | 5m (قصير المدى)" in report
    assert '*' not in report and '}' not in report