import pytest
from src.reporting.report_builder import ReportBuilder
from src.decision_engine.trade_setup import TradeSetup
from src.config import get_config

@pytest.fixture
def config():
    """Provides the application configuration."""
    return get_config()

@pytest.fixture
def report_builder(config):
    """Provides a ReportBuilder instance."""
    return ReportBuilder(config)

@pytest.fixture
def sample_trade_setup():
    """Provides a sample TradeSetup object."""
    return TradeSetup(
        chat_id=123,
        symbol="BTC/USDT",
        timeframe="1h",
        pattern_name="نموذج علم صاعد",
        pattern_status="مفعل",
        entry_price=50000.0,
        stop_loss=48000.0,
        target1=55000.0,
        target2=58000.0,
        confirmation_conditions=[
            "✅ حجم تداول مرتفع عند الاختراق يؤكد الزخم.",
            "✅ السعر يتداول فوق المتوسطات المتحركة الرئيسية (20, 50)."
        ]
    )

def test_format_trade_setup(report_builder, sample_trade_setup):
    """Tests the _format_trade_setup method."""
    report_text = report_builder._format_trade_setup(sample_trade_setup)

    assert "تفاصيل الصفقة المقترحة" in report_text
    assert "النموذج:** نموذج علم صاعد (مفعل)" in report_text
    assert "سعر الدخول:** $50,000.00" in report_text
    assert "وقف الخسارة:** $48,000.00" in report_text
    assert "الأهداف:** $55,000.00 | $58,000.00" in report_text
    assert "شروط تأكيد الدخول" in report_text
    assert "حجم تداول مرتفع" in report_text
    assert "فوق المتوسطات المتحركة" in report_text

def test_build_report_with_trade_setup(report_builder, sample_trade_setup):
    """
    Tests that the main build_report method correctly includes the
    formatted trade setup in one of its timeframe sections.
    """
    mock_ranked_results = [
        {
            "timeframe": "1h",
            "symbol": "BTC/USDT",
            "current_price": 50100.0,
            "raw_analysis": {
                "patterns": [],
                "supports": [],
                "resistances": []
            },
            "trade_setup": sample_trade_setup
        }
    ]
    mock_general_info = {
        "symbol": "BTC/USDT",
        "current_price": 50100.0,
        "analysis_type": "تحليل شامل",
        "timeframes": ["1h"]
    }

    full_report = report_builder.build_report(mock_ranked_results, mock_general_info)

    timeframe_report = full_report["timeframe_reports"][0]

    assert "تفاصيل الصفقة المقترحة" in timeframe_report
    assert "سعر الدخول:** $50,000.00" in timeframe_report
