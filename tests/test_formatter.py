import pytest
from src.utils.formatter import format_analysis_from_template

@pytest.fixture
def mock_buy_analysis_data():
    """Provides a mock analysis_data dictionary for a BUY signal."""
    return {
        "signal": "BUY",
        "fibo_trend": "up",
        "final_reason": "فرصة شراء عالية الثقة.",
        "scenarios": {
            "scenario1": {
                "entry_zone": {"start": 65500, "end": 64800, "best": 64800},
                "stop_loss": 63900,
                "targets": {"tp1": 67100, "tp2": 68500, "tp3": 70000}
            }
        },
        "rr_ratio": 2.5,
        "confidence": 75,
        "trend": "up",
        "higher_tf_trend_info": {"trend": "up", "timeframe": "1D"},
        "latest_data": {"adx": 28.5, "rsi": 58.2, "macd": 1, "signal_line": 0},
        "reasons": ["اتجاه صاعد قوي.", "نمط ابتلاع شرائي."],
        "weights": {"a": 1, "b": 2},
        "key_levels": [
            {'level': 68000, 'type': 'Resistance'},
            {'level': 67100, 'type': 'Resistance'},
            {'level': 65500, 'type': 'Support'},
        ],
        "current_price": 66100,
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
    }

@pytest.fixture
def mock_hold_analysis_data():
    """Provides a mock analysis_data dictionary for a HOLD signal."""
    return {
        "signal": "HOLD",
        "final_reason": "السوق في حالة تذبذب.",
        "scenarios": {
            "scenario1": {"targets": {"tp1": 70000}},
            "scenario2": {"target": 61500}
        },
        "trend": "sideways",
        "higher_tf_trend_info": None,
        "latest_data": {"adx": 18.0, "rsi": 51.0, "macd": 1, "signal_line": 1},
        "reasons": [],
        "weights": {"a": 1, "b": 2},
        "key_levels": [],
        "current_price": 66000,
        "swing_high": {"price": 68000},
        "swing_low": {"price": 63000},
    }

def test_format_report_for_buy_signal(mock_buy_analysis_data):
    """
    Tests that the formatter correctly generates a report for a BUY signal
    with the new 'trade plan' structure.
    """
    # Act
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="ar")

    # Assert
    assert "الخلاصة التنفيذية" in report
    assert "خطة التداول المقترحة" in report
    assert "منطقة الدخول" in report
    assert "65,500 - 64,800" in report
    assert "الأهداف (TP)" in report
    assert "TP1: **67,100**" in report
    assert "خطة المراقبة" not in report  # Ensure monitoring plan is not shown

def test_format_report_for_hold_signal(mock_hold_analysis_data):
    """
    Tests that the formatter correctly generates a report for a HOLD signal
    with the new 'monitoring plan' structure.
    """
    # Act
    report = format_analysis_from_template(mock_hold_analysis_data, "BTC/USDT", "4H", lang="ar")

    # Assert
    assert "الخلاصة التنفيذية" in report
    assert "خطة المراقبة" in report
    assert "السيناريو الصاعد (للمراقبة)" in report
    assert "شرط التفعيل" in report
    assert "فوق مستوى المقاومة **68,000**" in report
    assert "خطة التداول المقترحة" not in report  # Ensure trade plan is not shown
    assert "لا توجد مؤشرات قوة إضافية حاليًا." in report

def test_format_report_english_translation(mock_buy_analysis_data):
    """
    Tests that the formatter correctly uses the English translations.
    """
    # Act
    report = format_analysis_from_template(mock_buy_analysis_data, "BTC/USDT", "4H", lang="en")

    # Assert
    assert "Executive Summary" in report
    assert "Suggested Trade Plan" in report
    assert "Entry Zone" in report
    assert "Targets (TP)" in report
    assert "Monitoring Plan" not in report