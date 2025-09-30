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
        "key_support": 64000,
        "key_resistance": 67000,
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
        "key_support": 63500,
        "key_resistance": 67500,
    }

def test_format_buy_signal_report_is_correct(mock_buy_analysis_data):
    """
    Tests that a BUY signal report is correctly formatted with the 'Informed Decision' template.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H")

    # --- Assertions for BUY signal ---
    assert "**تحليل شامل وقرار تداول: BTC/USDT | 4H (طويل المدى)**" in report
    assert "**النوع:** **BUY**" in report
    assert "**الثقة:** 85%" in report
    assert "أهم دعم:** 64,000" in report
    assert "أهم مقاومة:** 67,000" in report
    # Check that trade details are populated
    assert "الدخول:** 64,800" in report
    assert "وقف الخسارة:** 63,900" in report
    assert "الأهداف:** 67,100 | 68,500" in report
    # Check that no placeholders are left
    assert '{' not in report and '}' not in report

def test_format_hold_signal_report_is_correct(mock_hold_analysis_data):
    """
    Tests that a HOLD signal report correctly displays 'N/A' for trade details.
    """
    report = format_analysis_from_template(mock_hold_analysis_data, "ETH/USDT", "1D")

    # --- Assertions for HOLD signal ---
    assert "**تحليل شامل وقرار تداول: ETH/USDT | 1D (طويل المدى)**" in report
    assert "**النوع:** **HOLD**" in report
    assert "**الثقة:** 40%" in report
    assert "أهم دعم:** 63,500" in report
    # Check that trade details are 'N/A'
    assert "الدخول:** N/A" in report
    assert "وقف الخسارة:** N/A" in report
    assert "الأهداف:** N/A | N/A" in report
    # Check that no placeholders are left
    assert '{' not in report and '}' not in report

def test_formatter_selects_short_term_template_correctly(mock_buy_analysis_data):
    """
    Tests that the formatter selects the short-term template for a short-term timeframe.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "SOL/USDT", "5m")
    assert "**تحليل شامل وقرار تداول: SOL/USDT | 5m (قصير المدى)**" in report
    assert '{' not in report and '}' not in report