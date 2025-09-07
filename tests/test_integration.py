import pytest
from unittest.mock import patch
import pandas as pd

from src.config import get_config
from src.data.okx_fetcher import OKXDataFetcher
from src.analysis import AnalysisOrchestrator, TechnicalIndicators, TrendAnalysis # etc.
from src.decision_engine.engine import DecisionEngine
from src.app import main as cli_main

@pytest.fixture
def mock_fetcher(mocker):
    # ...
    pass

def test_cli_app_runs_without_crashing(mocker):
    mocker.patch('src.notifiers.telegram_sender.SimpleTelegramNotifier.send', return_value=True)
    mocker.patch('argparse.ArgumentParser.parse_args', return_value=mocker.MagicMock(symbols=['BTC/USDT']))

    config = get_config()
    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        # All other modules initialized without df
    ]
    orchestrator = AnalysisOrchestrator(analysis_modules)
    decision_engine = DecisionEngine(config)

    # Mock the fetcher completely
    fetcher = mocker.MagicMock(spec=OKXDataFetcher)
    fetcher.fetch_historical_data.return_value = pd.DataFrame({'close': [1,2,3]*40}) # dummy df

    cli_main(
        config=config,
        fetcher=fetcher,
        orchestrator=orchestrator,
        decision_engine=decision_engine
    )
