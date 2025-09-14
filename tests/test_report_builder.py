import pytest
from src.reporting.report_builder import ReportBuilder
from src.config import get_config
from src.analysis.data_models import Level

@pytest.fixture
def config():
    """Provides the application configuration."""
    return get_config()

@pytest.fixture
def report_builder(config):
    """Provides a ReportBuilder instance."""
    return ReportBuilder(config)

def test_build_report_fills_all_placeholders(report_builder):
    """
    Tests that the build_report function correctly fills the template
    placeholders with data using the robust keyword-based matching.
    """
    # This data simulates a result from the analysis orchestrator
    ranked_results = [
        {
            'timeframe': '1h',
            'raw_analysis': {
                'supports': [
                    Level(name='Fibonacci Support 0.618', value=60000.0, level_type='support', quality='Strong'),
                    Level(name='دعم القناة السعرية', value=61000.0, level_type='support', quality='Medium'),
                ],
                'resistances': [
                    Level(name='Some other Fibonacci Resistance 1.618', value=70000.0, level_type='resistance', quality='Strong'),
                    Level(name='A pattern target level', value=72000.0, level_type='resistance', quality='Medium')
                ],
                'patterns': []
            }
        }
    ]
    general_info = {
        'symbol': 'BTC/USDT',
        'current_price': 65000.0,
        'analysis_type': 'استثمار طويل المدى' # Use Arabic name to test the whole fix
    }

    messages = report_builder.build_report(ranked_results, general_info)

    # Convert messages to a single string to check for content
    full_report = " ".join([msg['content'] for msg in messages])

    # Check that there is no error message
    assert not any("لم يتم العثور على قالب" in msg.get('content', '') for msg in messages)

    # Check that placeholders for matched levels are filled
    assert '- دعم فيبو 0.618: $60,000.00' in full_report
    assert '- دعم قناة سعرية: $61,000.00' in full_report
    assert '- مقاومة فيبو 1.618: $70,000.00' in full_report
    assert '- مقاومة هدف النموذج: $72,000.00' in full_report

    # Check that an unmatched placeholder is still filled with "N/A"
    assert '- دعم فيبو 0.5: N/A' in full_report
