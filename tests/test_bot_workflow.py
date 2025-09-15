import sys
import os
import pytest
import anyio

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_config
from src.data_retrieval.okx_fetcher import OKXDataFetcher
from src.analysis.orchestrator import AnalysisOrchestrator
from src.decision_engine.engine import DecisionEngine
from src.notifiers.telegram_notifier import InteractiveTelegramBot
from src.analysis import (
    TrendAnalysis, PriceChannels,
    NewSupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
)
from src.indicators.technical_score import TechnicalIndicators

@pytest.fixture(scope="module")
def core_components():
    """Initializes and provides all core components needed for the test."""
    config = get_config()
    fetcher = OKXDataFetcher(config)

    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        PriceChannels(config=config.get('analysis')),
        NewSupportResistanceAnalysis(config=config.get('analysis')),
        FibonacciAnalysis(config=config.get('analysis')),
        ClassicPatterns(config=config.get('analysis')),
        TrendLineAnalysis(config=config.get('analysis'))
    ]
    orchestrator = AnalysisOrchestrator(analysis_modules)
    decision_engine = DecisionEngine(config)

    fetcher.start_data_services(['BTC-USDT'])
    yield config, fetcher, orchestrator, decision_engine
    fetcher.stop()


@pytest.mark.anyio
async def test_bot_full_analysis_workflow(core_components):
    """
    Tests the entire analysis and reporting workflow as triggered by the bot.
    """
    config, fetcher, orchestrator, decision_engine = core_components
    await anyio.sleep(10) # Wait for data services

    bot = InteractiveTelegramBot(
        config=config,
        fetcher=fetcher,
        orchestrator=orchestrator,
        decision_engine=decision_engine
    )

    symbol = 'BTC/USDT'
    timeframes = get_config()['trading']['TIMEFRAME_GROUPS']['long_term']
    analysis_type = "long_term"
    chat_id = 12345

    # --- Execute ---
    report_messages, ranked_recs = await bot._run_analysis_for_request(chat_id, symbol, timeframes, analysis_type)

    # --- Verify ---
    assert isinstance(report_messages, list), "The report should be a list of message dictionaries."
    assert len(report_messages) > 0, "The report should contain at least one message."

    # Check that there are no errors
    assert not any("error" in msg for msg in report_messages), f"The analysis workflow returned an error."

    # Check the structure and content of the messages
    assert len(report_messages) == 1 + len(timeframes) + 1 # Header + Timeframes + Summary

    header = report_messages[0]
    assert header['type'] == 'header'
    assert '💎 تحليل فني شامل' in header['content']
    assert symbol in header['content']

    timeframe_messages = report_messages[1:-1]
    assert len(timeframe_messages) == len(timeframes)

    expected_level_names = {
            "دعم ترند قصير", "دعم ترند متوسط", "دعم ترند طويل",
            "دعم قناة سعرية", "دعم فيبو 0.618", "دعم فيبو 0.5",
            "منطقة طلب عالية", "دعم عام سابق", "مقاومة رئيسية",
            "مقاومة هدف النموذج", "مقاومة فيبو 1.0", "مقاومة فيبو 1.172",
            "مقاومة فيبو 1.618", "منطقة عرض عالية"
    }

    for msg in timeframe_messages:
        assert msg['type'] == 'timeframe'
        assert 'n' not in msg['content'], "The timeframe message should not contain 'n' characters."

        lines = msg['content'].split('\n')
        for line in lines:
            if line.startswith('- '):
                level_name = line.split(':')[0][2:] # Remove '- ' prefix
                assert level_name in expected_level_names, f"Unexpected level name: {level_name}"

    final_summary = report_messages[-1]
    assert final_summary['type'] == 'final_summary'
    assert '📌 الملخص التنفيذي والشامل' in final_summary['content']
    assert 'نقاط المراقبة الحرجة:' in final_summary['content']
    # Check that there is some data after the critical points label
    assert len(final_summary['content'].split('نقاط المراقبة الحرجة:')[1].strip()) > 0
    assert 'keyboard' in final_summary
