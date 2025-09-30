import pytest
from src.utils.formatter import format_analysis_from_template
from src.localization import get_text

# Fixtures provide mock data for different scenarios.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal using the new structured format."""
    return {
        "signal": "BUY", "fibo_trend": "up",
        "final_reason": {'key': 'final_reason_signal_confirmed', 'context': {'score': 8, 'trend': 'up'}},
        "scenarios": {
            "scenario1": {
                "title_key": "scenario_title_up_primary",
                "entry_zone": {"start": 65500, "end": 64800, "best": 64800},
                "stop_loss": 63900,
                "targets": {"tp1": 67100, "tp2": 68500, "tp3": 70000}
            },
            "scenario2": {"title_key": "scenario_title_up_secondary"}
        },
        "rr_ratio": 2.5, "confidence": 75, "trend": "up",
        "higher_tf_trend_info": {"trend": "up", "timeframe": "1D"},
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0},
        "reasons": [
            {'key': 'reason_rsi_confirm_up', 'context': {'value': '58.2'}},
            {'key': 'reason_pattern_confirm_down', 'context': {'pattern': 'Bullish Engulfing'}}
        ],
        "weights": {"a": 1, "b": 2},
        "key_levels": [
            {'level': 68000, 'type': 'Resistance'},
            {'level': 65500, 'type': 'Support'},
        ],
        "current_price": 66100, "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
    }

@pytest.fixture
def mock_buy_analysis_data_en(mock_buy_analysis_data):
    """Reuses the structured BUY data for English tests."""
    return mock_buy_analysis_data

@pytest.fixture
def mock_hold_analysis_data():
    """Provides a mock analysis_data dictionary for a HOLD signal using the new structured format."""
    return {
        "signal": "HOLD",
        "final_reason": {'key': 'final_reason_score_not_met', 'context': {'score': 3, 'threshold': 5}},
        "scenarios": {
            "scenario1": {"title_key": "scenario_title_up_primary_hold", "targets": {"tp1": 70000}},
            "scenario2": {"title_key": "scenario_title_up_secondary_hold", "target": 61500, "stop_loss": 68000}
        },
        "trend": "sideways", "higher_tf_trend_info": None,
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1},
        "reasons": [], "weights": {"a": 1, "b": 2}, "key_levels": [],
        "current_price": 66000, "swing_high": {"price": 68000}, "swing_low": {"price": 63000},
    }

def test_format_report_for_buy_signal_is_complete(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates a complete report for a BUY signal
    with no leftover placeholders.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="ar")

    # Check for a key part of the trade plan section
    assert get_text("section_trade_plan_title", "ar") in report
    # Check for a translated reason
    expected_reason = get_text('reason_rsi_confirm_up', 'ar').format(value='58.2')
    assert expected_reason in report
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_format_report_for_hold_signal_is_complete(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates a complete report for a HOLD signal
    with no leftover placeholders.
    """
    report = format_analysis_from_template(mock_hold_analysis_data, "BTC/USDT", "4H", lang="ar")

    assert get_text("section_monitoring_plan_title", "ar") in report
    assert get_text("details_no_strength_reasons", "ar") in report
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."

def test_format_report_english_translation_is_complete(mock_buy_analysis_data_en):
    """
    Tests that the formatter correctly uses English translations and leaves no placeholders.
    """
    report = format_analysis_from_template(mock_buy_analysis_data_en, "BTC/USDT", "4H", lang="en")

    assert get_text("section_trade_plan_title", "en") in report
    # Check for a translated reason in English
    expected_reason = get_text('reason_rsi_confirm_up', 'en').format(value='58.2')
    assert expected_reason in report
    assert '{' not in report, "The report should not contain any leftover '{' placeholders."
    assert '}' not in report, "The report should not contain any leftover '}' placeholders."