import pytest
from src.utils.formatter import format_analysis_from_template

# Fixtures provide mock data that closely resembles the output of FiboAnalyzer.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a realistic mock analysis_data for a BUY signal with higher timeframe info."""
    return {
        "signal": "BUY", "confidence": 85.0, "pattern": "Bullish Engulfing",
        "higher_tf_trend_info": {"trend": "up", "timeframe": "1D"},
        "final_reason": {'key': 'final_reason_signal_confirmed'},
        "scenarios": {"scenario1": {"entry_zone": {"best": 64800}, "stop_loss": 63900, "targets": {"tp1": 67100, "tp2": 68500}}},
        "trend": "up",
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0, "stoch_k": 60, "stoch_d": 55, "volume": 120, "volume_sma": 100},
        "current_price": 66100,
        "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
        "retracements": {"fib_382": 64000, "fib_500": 64500, "fib_618": 65000}
    }

@pytest.fixture
def mock_hold_analysis_data_no_htf():
    """Provides a realistic mock analysis_data for a HOLD signal *without* higher timeframe info."""
    return {
        "signal": "HOLD", "confidence": 40.0, "pattern": "Doji",
        "higher_tf_trend_info": None, # Explicitly None
        "final_reason": {'key': 'final_reason_score_not_met'},
        "scenarios": {"scenario1": {}, "scenario2": {}},
        "trend": "sideways",
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1, "stoch_k": 50, "stoch_d": 52, "volume": 80, "volume_sma": 100},
        "current_price": 66000,
        "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
        "retracements": {"fib_382": 64000, "fib_500": 64500, "fib_618": 65000}
    }

def test_format_buy_signal_is_correct_and_complete(mock_buy_analysis_data):
    """
    Tests a BUY signal report for correct translation, dynamic sections, and completeness.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H")

    # --- Assertions for BUY signal ---
    assert "**تحليل BTC/USDT | الإطار الزمني: 4H (طويل المدى)**" in report
    assert "**الإشارة:** **BUY**" in report
    # Check for smart summary translation
    assert "إشارة buy قوية مدعومة بتوافق المؤشرات الفنية." in report
    # Check that higher timeframe info IS present
    assert "اتجاه الفريم الأعلى (1D):** UP" in report
    # Check that the recommendation section IS present
    assert "**توصية التداول**" in report
    assert "**الدخول:** 64,800" in report
    # Check that no placeholders are left
    assert '{' not in report and '}' not in report

def test_format_hold_signal_hides_dynamic_sections_correctly(mock_hold_analysis_data_no_htf):
    """
    Tests a HOLD signal report hides trade recommendations and dynamic confirmation lines
    when their data is unavailable.
    """
    report = format_analysis_from_template(mock_hold_analysis_data_no_htf, "ETH/USDT", "1D")

    # --- Assertions for HOLD signal ---
    assert "**الإشارة:** **HOLD**" in report
    # Check for default user-friendly summary
    assert "لا توجد إشارة واضحة حاليًا. يوصى بالمراقبة." in report
    # Check that higher timeframe info is NOT present
    assert "اتجاه الفريم الأعلى" not in report
    # Check that the recommendation section is NOT present
    assert "**توصية التداول**" not in report
    # Check that no placeholders are left
    assert '{' not in report and '}' not in report

def test_formatter_selects_short_term_template_correctly(mock_buy_analysis_data):
    """
    Tests that the formatter selects the short-term template for a short-term timeframe.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "SOL/USDT", "5m")
    assert "**تحليل SOL/USDT | الإطار الزمني: 5m (قصير المدى)**" in report
    assert '{' not in report and '}' not in report