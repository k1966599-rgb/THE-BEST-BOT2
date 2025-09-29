import pytest
from src.utils.formatter import format_analysis_from_template
from src.localization import get_text

# Fixtures provide mock data for different scenarios.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal in Arabic."""
    return {
        "signal": "BUY", "fibo_trend": "up", "final_reason": "فرصة شراء عالية الثقة.",
        "scenarios": {
            "scenario1": {
                "entry_zone": {"start": 65500, "end": 64800, "best": 64800},
                "stop_loss": 63900,
                "targets": {"tp1": 67100, "tp2": 68500, "tp3": 70000}
            },
            "scenario2": {}
        },
        "rr_ratio": 2.5, "confidence": 75, "trend": "up",
        "higher_tf_trend_info": {"trend": "up", "timeframe": "1D"},
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0},
        "reasons": ["اتجاه صاعد قوي.", "نمط ابتلاع شرائي."],
        "weights": {"a": 1, "b": 2},
        "key_levels": [
            {'level': 68000, 'type': 'Resistance'},
            {'level': 65500, 'type': 'Support'},
        ],
        "current_price": 66100, "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
    }

@pytest.fixture
def mock_buy_analysis_data_en(mock_buy_analysis_data):
    """
    Provides a mock analysis_data dictionary for a BUY signal with English reasons.
    This fixture depends on mock_buy_analysis_data.
    """
    # Pytest injects the result of mock_buy_analysis_data here
    data = mock_buy_analysis_data
    data['reasons'] = ["Strong upward trend.", "Bullish engulfing pattern."]
    return data

@pytest.fixture
def mock_hold_analysis_data():
    """Provides a mock analysis_data dictionary for a HOLD signal."""
    return {
        "signal": "HOLD", "final_reason": "السوق في حالة تذبذب.",
        "scenarios": {
            "scenario1": {"targets": {"tp1": 70000}},
            "scenario2": {"target": 61500, "stop_loss": 68000}
        },
        "trend": "sideways", "higher_tf_trend_info": None,
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1},
        "reasons": [], "weights": {"a": 1, "b": 2}, "key_levels": [],
        "current_price": 66000, "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
    }

def test_format_report_for_buy_signal_is_complete(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates a complete and valid report for a BUY signal.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="ar")

    assert get_text("section_summary_title", "ar") in report
    assert get_text("section_trade_plan_title", "ar") in report
    assert "اتجاه صاعد قوي." in report

def test_format_report_for_hold_signal_is_complete(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates a complete and valid report for a HOLD signal.
    """
    report = format_analysis_from_template(mock_hold_analysis_data, "BTC/USDT", "4H", lang="ar")

    assert get_text("section_monitoring_plan_title", "ar") in report
    assert get_text("details_no_strength_reasons", "ar") in report
    assert get_text("section_trade_plan_title", "ar") not in report

def test_format_report_english_translation_is_complete(mock_buy_analysis_data_en):
    """
    Tests that the formatter correctly uses the English translations for a complete report.
    """
    report = format_analysis_from_template(mock_buy_analysis_data_en, "BTC/USDT", "4H", lang="en")

    assert get_text("section_summary_title", "en") in report
    assert get_text("section_trade_plan_title", "en") in report
    assert "Strong upward trend." in report
    assert get_text("section_monitoring_plan_title", "en") not in report