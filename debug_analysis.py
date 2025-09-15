import json
from src.config import get_config
from src.data_retrieval.okx_fetcher import OKXDataFetcher
from src.analysis.orchestrator import AnalysisOrchestrator
import pandas as pd
from src.utils.data_preprocessor import standardize_dataframe_columns

def main():
    config = get_config()
    fetcher = OKXDataFetcher(config)

    all_support_names = set()
    all_resistance_names = set()

    timeframes_to_check = ['1H', '4H', '1D']

    for timeframe in timeframes_to_check:
        print(f"--- Analyzing {timeframe} ---")
        # Initialize analysis modules for the current timeframe
        from src.analysis import (
            TrendAnalysis, PriceChannels,
            NewSupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
        )
        from src.indicators.technical_score import TechnicalIndicators
        from src.indicators.volume_profile import VolumeProfileAnalysis

        # Convert to lowercase for config lookup
        tf_lower = timeframe.lower().replace('h', 'h')

        analysis_modules = [
            TechnicalIndicators(config=config.get('analysis'), timeframe=tf_lower),
            TrendAnalysis(config=config.get('analysis'), timeframe=tf_lower),
            PriceChannels(config=config.get('analysis'), timeframe=tf_lower),
            NewSupportResistanceAnalysis(config=config.get('analysis'), timeframe=tf_lower),
            FibonacciAnalysis(config=config.get('analysis'), timeframe=tf_lower),
            ClassicPatterns(config=config.get('analysis'), timeframe=tf_lower),
            TrendLineAnalysis(config=config.get('analysis'), timeframe=tf_lower),
            VolumeProfileAnalysis(config=config.get('analysis'), timeframe=tf_lower)
        ]
        orchestrator = AnalysisOrchestrator(analysis_modules)

        symbol = 'BTC-USDT'

        historical_data = fetcher.fetch_historical_data(symbol=symbol, timeframe=timeframe)
        if not historical_data or not historical_data.get('data'):
            print(f"Could not fetch data for {timeframe}")
            continue

        df = pd.DataFrame(historical_data['data'])
        df = standardize_dataframe_columns(df)
        df.set_index('timestamp', inplace=True)

        analysis_results = orchestrator.run(df)

        for support in analysis_results.get('supports', []):
            all_support_names.add(support.name)
        for resistance in analysis_results.get('resistances', []):
            all_resistance_names.add(resistance.name)

    print("\n\n--- Unique Support Names ---")
    for name in sorted(list(all_support_names)):
        print(name)

    print("\n\n--- Unique Resistance Names ---")
    for name in sorted(list(all_resistance_names)):
        print(name)


if __name__ == "__main__":
    main()
