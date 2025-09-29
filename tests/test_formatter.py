import pytest
from src.utils.formatter import format_analysis_from_template

# Fixtures provide mock data for different scenarios.
@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal."""
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

def test_format_report_for_buy_signal_structure(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates all sections for a BUY signal.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="ar")

    # Check for all section titles
    assert "1. الخلاصة التنفيذية" in report
    assert "2. خطة التداول المقترحة" in report
    assert "3. تفاصيل التحليل الفني" in report
    assert "4. مستويات الدعم والمقاومة" in report

    # Check for specific content in the trade plan
    assert "منطق الصفقة" in report
    assert "منطقة الدخول" in report
    assert "الأهداف (TP)" in report
    assert "TP1: **67,100**" in report

    # Ensure the monitoring plan is NOT present
    assert "خطة المراقبة" not in report

def test_format_report_for_hold_signal_structure(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates all sections for a HOLD signal.
    """
    report = format_analysis_from_template(mock_hold_analysis_data, "BTC/USDT", "4H", lang="ar")

    # Check for all section titles
    assert "1. الخلاصة التنفيذية" in report
    assert "2. خطة المراقبة" in report
    assert "3. تفاصيل التحليل الفني" in report
    assert "4. مستويات الدعم والمقاومة" in report

    # Check for specific content in the monitoring plan
    assert "السيناريو الصاعد (للمراقبة)" in report
    assert "شرط التفعيل" in report
    assert "فوق مستوى المقاومة **68,000**" in report

    # Check that the "no reasons" text is present
    assert "لا توجد مؤشرات قوة إضافية حاليًا." in report

    # Ensure the trade plan is NOT present
    assert "خطة التداول المقترحة" not in report

def test_format_report_english_translation_structure(mock_buy_analysis_data):
    """
    Tests that the formatter correctly uses the English translations for all sections.
    """
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="en")

    # Check for all section titles in English
    assert "1. Executive Summary" in report
    assert "2. Suggested Trade Plan" in report
    assert "3. Technical Analysis Details" in report
    assert "4. Key Support & Resistance Levels" in report

    # Check for specific content in the English trade plan
    assert "Trade Rationale" in report
    assert "Entry Zone" in report
    assert "Targets (TP)" in report

    # Ensure the monitoring plan is NOT present
    assert "Monitoring Plan" not in report