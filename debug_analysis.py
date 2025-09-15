import json
from src.config import get_config
from src.data_retrieval.okx_fetcher import OKXDataFetcher
from src.analysis.orchestrator import AnalysisOrchestrator
from src.decision_engine.engine import DecisionEngine
import pandas as pd
from src.utils.data_preprocessor import standardize_dataframe_columns

def main():
    config = get_config()
    fetcher = OKXDataFetcher(config)

    # Initialize analysis modules
    from src.analysis import (
        TrendAnalysis, PriceChannels,
        NewSupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
    )
    from src.indicators.technical_score import TechnicalIndicators
    from src.indicators.volume_profile import VolumeProfileAnalysis

    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis'), timeframe='1h'),
        PriceChannels(config=config.get('analysis'), timeframe='1h'),
        NewSupportResistanceAnalysis(config=config.get('analysis'), timeframe='1h'),
        FibonacciAnalysis(config=config.get('analysis'), timeframe='1h'),
        ClassicPatterns(config=config.get('analysis'), timeframe='1h'),
        TrendLineAnalysis(config=config.get('analysis'), timeframe='1h'),
        VolumeProfileAnalysis(config=config.get('analysis'), timeframe='1h')
    ]
    orchestrator = AnalysisOrchestrator(analysis_modules)

    symbol = 'BTC-USDT'
    timeframe = '1H' # Use API-compatible timeframe

    historical_data = fetcher.fetch_historical_data(symbol=symbol, timeframe=timeframe)
    df = pd.DataFrame(historical_data['data'])
    df = standardize_dataframe_columns(df)
    df.set_index('timestamp', inplace=True)

    analysis_results = orchestrator.run(df)

    print(json.dumps(analysis_results, indent=4, default=lambda o: o.__dict__))

if __name__ == "__main__":
    main()
