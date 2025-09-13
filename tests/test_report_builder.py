import pytest
from src.reporting.report_builder import ReportBuilder
from src.analysis.data_models import Level, Pattern
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

def test_format_levels_supports_with_new_names(report_builder):
    """
    Tests that support levels are formatted correctly according to the new user template,
    including context-aware names based on the pattern.
    """
    mock_pattern = Pattern(
        name="علم صاعد", status="Active", timeframe="4H",
        activation_level=114000.0, invalidation_level=111000.0, target1=117000.0
    )
    mock_levels = [
        Level(name="medium_term_trend_support", value=111000.0, level_type="support", quality="critical"),
        Level(name="channel_support", value=111500.0, level_type="support", quality="strong"),
        Level(name="fibonacci_support_0.618", value=112200.0, level_type="support", quality=None),
        Level(name="high volume node", value=111274.5, level_type="support", quality="medium"),
        Level(name="previous_support", value=108290.0, level_type="support", quality="secondary"),
    ]
    formatted_string = report_builder._format_levels(mock_levels, is_support=True, pattern=mock_pattern)
    expected_lines = {
        "دعم ترند متوسط: $111,000 (حرج)",
        "دعم قناة/قاع العلم: $111,500 (قوي)",
        "دعم فيبو 0.618: $112,200",
        "منطقة طلب عالية: $111,274 (متوسط)",
        "دعم عام سابق: $108,290 (ثانوي)"
    }
    output_lines = {line.strip() for line in formatted_string.strip().split('\n')}
    assert output_lines == expected_lines

def test_format_levels_resistances_with_new_names(report_builder):
    """
    Tests that resistance levels are formatted correctly.
    """
    mock_pattern = Pattern(
        name="مثلث صاعد", status="Forming", timeframe="1H",
        activation_level=112000.0, invalidation_level=110530.0, target1=115500.0
    )
    mock_levels = [
        Level(name="poc_resistance", value=112000.0, level_type="resistance", quality="critical"),
        Level(name="pattern_target", value=115500.0, level_type="resistance", quality="technical"),
        Level(name="fibonacci_resistance_1.618", value=120000.0, level_type="resistance", quality=None)
    ]
    formatted_string = report_builder._format_levels(mock_levels, is_support=False, pattern=mock_pattern)
    expected_lines = {
        "مقاومة رئيسية: $112,000 (حرج)",
        "مقاومة فيبو 1.618: $120,000",
        "مقاومة هدف النموذج: $115,500 (فني)"
    }
    output_lines = {line.strip() for line in formatted_string.strip().split('\n')}
    assert output_lines == expected_lines

def test_format_summary_section_with_three_targets(report_builder):
    """
    Tests that the summary section correctly formats the 'Confirmed Trade'
    part with three targets.
    """
    # 1. Arrange
    mock_trade_setup = TradeSetup(
        chat_id=123, symbol="BTC/USDT", timeframe="1H", pattern_name="مثلث صاعد",
        pattern_status="Active", entry_price=112000.0, stop_loss=110530.0,
        target1=115500.0, target2=117500.0, target3=120000.0
    )
    mock_ranked_results = [{
        "timeframe": "1H",
        "raw_analysis": {"patterns": [Pattern(name="مثلث صاعد", status="قيد التكوين", timeframe="1H", activation_level=112000.0, invalidation_level=110530.0, target1=115500.0, target2=117500.0, target3=120000.0)]},
        "trade_setup": mock_trade_setup
    }]

    # 2. Act
    summary_text, _ = report_builder._format_summary_section(mock_ranked_results)

    # 3. Assert
    # Check that the targets line is correctly formatted
    expected_targets_line = "الأهداف: $115,500 → $117,500 → $120,000"
    assert expected_targets_line in summary_text

    # Check the stop loss as well
    expected_stop_loss_line = "وقف الخسارة: عند كسر $110,530"
    assert expected_stop_loss_line in summary_text
