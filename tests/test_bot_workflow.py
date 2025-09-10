import sys
import os
import pytest
import anyio

# HACK: Add project root to path to allow absolute imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_config
from src.data.okx_fetcher import OKXDataFetcher
from src.analysis.orchestrator import AnalysisOrchestrator
from src.decision_engine.engine import DecisionEngine
from src.notifiers.telegram_notifier import InteractiveTelegramBot
from src.analysis import (
    TechnicalIndicators, TrendAnalysis, PriceChannels,
    SupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
)

@pytest.fixture(scope="module")
def core_components():
    """Initializes and provides all core components needed for the test."""
    config = get_config()
    fetcher = OKXDataFetcher()

    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        PriceChannels(config=config.get('analysis')),
        SupportResistanceAnalysis(config=config.get('analysis')),
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
    timeframes = get_config()['trading']['TIMEFRAME_GROUPS']['medium']
    analysis_type = "تحليل متوسط المدى"
    chat_id = 12345

    # --- Execute ---
    report = await bot._run_analysis_for_request(chat_id, symbol, timeframes, analysis_type)

    # --- Verify ---
    assert 'error' not in report, f"The analysis workflow returned an error: {report.get('error')}"
    assert isinstance(report, dict), "Report should be a dictionary."

    # Check for the completeness of the new report structure
    expected_keys = ['header', 'timeframe_reports', 'summary', 'final_recommendation', 'ranked_results']
    for key in expected_keys:
        assert key in report, f"Report must contain key: '{key}'"

    # Check that the content is non-empty
    assert report["header"].strip() != ""
    assert isinstance(report["timeframe_reports"], list)
    assert len(report["timeframe_reports"]) == len(timeframes)
    assert report["summary"].strip() != ""
    assert report["final_recommendation"].strip() != ""
