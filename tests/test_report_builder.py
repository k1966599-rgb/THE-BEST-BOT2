import pytest
import pandas as pd
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

def test_format_levels_with_new_mapping(report_builder):
    """
    Tests the refactored _format_levels method with a variety of level types
    and qualities to ensure the new mapping works correctly.
    """
    # Arrange
    mock_pattern = Pattern(
        name="علم صاعد", status="Active", timeframe="4H",
        activation_level=114000.0, invalidation_level=111500.0, target1=117000.0
    )

    mock_supports = [
        Level(name="short_term_trend", value=110530.0, level_type="support", quality="critical"),
        Level(name="channel_support", value=111500.0, level_type="support", quality="strong"), # Should be renamed by pattern
        Level(name="fibonacci_support_0.618", value=110920.0, level_type="support", quality="قوي"),
        Level(name="previous_support", value=109130.0, level_type="support", quality="secondary"),
        Level(name="historical_support", value=107458.0, level_type="support", quality="strong"),
    ]

    mock_resistances = [
        Level(name="poc_resistance", value=112000.0, level_type="resistance", quality="critical"),
        Level(name="pattern_target", value=115500.0, level_type="resistance", quality="technical"),
        Level(name="some_resistance", value=125000.0, level_type="resistance", quality="hvn"),
        Level(name="channel_resistance", value=128000.0, level_type="resistance", quality="أعلى"),
    ]

    # Act
    support_string = report_builder._format_levels(mock_supports, is_support=True, pattern=mock_pattern)
    resistance_string = report_builder._format_levels(mock_resistances, is_support=False, pattern=mock_pattern)

    # Assert Supports
    expected_supports = {
        "دعم ترند قصير المدى: $110,530 (حرج)",
        "دعم قناة/قاع العلم: $111,500 (قوي)",
        "دعم فيبو 0.618: $110,920 (قوي)",
        "دعم عام سابق: $109,130 (ثانوي)",
        "دعم تاريخي: $107,458 (قوي)",
    }
    output_supports = {line.strip() for line in support_string.strip().split('\n')}
    assert output_supports == expected_supports

    # Assert Resistances
    expected_resistances = {
        "مقاومة رئيسية: $112,000 (حرج)",
        "مقاومة هدف النموذج: $115,500 (فني)",
        "منطقة عرض عالية: $125,000 (حجم تداول عالٍ)",
        "مقاومة القناة السعرية: $128,000 (الحد العلوي)",
    }
    output_resistances = {line.strip() for line in resistance_string.strip().split('\n')}
    assert output_resistances == expected_resistances

def test_summary_and_strategy_formatting(report_builder):
    """
    Tests the summary and strategy sections to ensure they are formatted correctly.
    """
    mock_trade_setup = TradeSetup(
        chat_id=123, symbol="BTC/USDT", timeframe="1H", pattern_name="مثلث صاعد",
        pattern_status="Active", entry_price=112000.0, stop_loss=110530.0,
        target1=115500.0, target2=117500.0, target3=120000.0
    )
    mock_ranked_results = [
        {
            "timeframe": "1H",
            "raw_analysis": {"patterns": [Pattern(name="مثلث صاعد", status="قيد التكوين", timeframe="1H", activation_level=112000.0, invalidation_level=110530.0, target1=115500.0, target2=117500.0, target3=120000.0)]},
            "trade_setup": mock_trade_setup
        },
        {
            "timeframe": "4H",
            "raw_analysis": {"patterns": [Pattern(name="علم صاعد", status="مفعل", timeframe="4H", activation_level=114000.0, invalidation_level=111000.0, target1=117000.0, target2=118300.0)]},
            "trade_setup": None
        }
    ]
    summary_text, _ = report_builder._format_summary_section(mock_ranked_results)

    assert "الأهداف: $115,500 → $117,500 → $120,000" in summary_text
    assert "استراتيجية دعم الفريمات: متابعة 4H لاختراق $114,000 للأهداف المتوسطة $117,000 – $118,300" in summary_text
