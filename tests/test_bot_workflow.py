import sys
import os
import pytest
import anyio

# HACK: This is a workaround for a project-wide architectural issue.
# The application uses absolute imports from the `src` directory (e.g., `from src.config...`),
# but it is also configured as an installable package where imports should not include `src`.
# This prevents pytest from finding the modules correctly. Adding the project root
# to the path is a temporary solution that allows tests to run.
# The long-term fix would be to remove the `src.` prefix from all imports project-wide.
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

    # Start data services needed for the test
    fetcher.start_data_services(['BTC-USDT'])

    yield config, fetcher, orchestrator, decision_engine

    # Teardown: stop data services
    print("\nStopping data services...")
    fetcher.stop()


@pytest.mark.anyio
async def test_bot_full_analysis_workflow(core_components):
    """
    Tests the entire analysis and reporting workflow as triggered by the bot.
    This simulates a user pressing a button to get a medium-term analysis for BTC.
    """
    config, fetcher, orchestrator, decision_engine = core_components

    # Give some time for the data services to fetch initial data
    await anyio.sleep(10)

    # Initialize the bot
    bot = InteractiveTelegramBot(
        config=config,
        fetcher=fetcher,
        orchestrator=orchestrator,
        decision_engine=decision_engine
    )

    # These are the parameters for a typical "medium-term" analysis request
    symbol = 'BTC/USDT'
    timeframes = get_config()['trading']['TIMEFRAME_GROUPS']['medium']
    analysis_type = "تحليل متوسط المدى"

    # --- Execute ---
    # Call the core function that the bot uses to generate a report
    report = await bot._run_analysis_for_request(symbol, timeframes, analysis_type)

    # --- Verify ---
    # 1. Check that the analysis didn't fail
    assert 'error' not in report, f"The analysis workflow returned an error: {report.get('error')}"
    assert report is not None, "The analysis report should not be None."
    assert isinstance(report, dict), "Report should be a dictionary."

    # 2. Check for the completeness of the report structure
    assert "header" in report, "Report must contain a 'header'."
    assert "timeframe_sections" in report, "Report must contain 'timeframe_sections'."
    assert "summary_and_recommendation" in report, "Report must contain a 'summary_and_recommendation'."

    # 3. Check that the content is non-empty
    assert report["header"].strip() != "", "Report header should not be empty."
    assert len(report["timeframe_sections"]) > 0, "There should be at least one timeframe section."
    assert report["summary_and_recommendation"].strip() != "", "Report summary should not be empty."

    # 4. Check that we have a report for each requested timeframe
    assert len(report["timeframe_sections"]) == len(timeframes), \
        f"Expected {len(timeframes)} timeframe reports, but got {len(report['timeframe_sections'])}."
