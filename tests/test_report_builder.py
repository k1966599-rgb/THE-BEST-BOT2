import pytest
from src.reporting.report_builder import ReportBuilder
from src.config import get_config

@pytest.fixture
def config():
    """Provides the application configuration."""
    return get_config()

@pytest.fixture
def report_builder(config):
    """Provides a ReportBuilder instance."""
    return ReportBuilder(config)

def test_build_report_with_arabic_analysis_type(report_builder):
    """
    Tests that the build_report function can handle an Arabic analysis_type name
    and still find the correct template.
    """
    ranked_results = []
    general_info = {
        'symbol': 'BTC/USDT',
        'current_price': 65000.0,
        'analysis_type': 'استثمار طويل المدى' # Arabic name
    }

    messages = report_builder.build_report(ranked_results, general_info)

    # Check that there is no error message
    assert not any("لم يتم العثور على قالب" in msg.get('content', '') for msg in messages)

    # Check that the header from the correct template is present
    assert "تحليل فني شامل" in messages[0]['content']
