import argparse
import time
import logging
from typing import List, Dict, Any
import pandas as pd

from .config import get_config, WATCHLIST
from .data.okx_fetcher import OKXDataFetcher
from .analysis.orchestrator import AnalysisOrchestrator
from .decision_engine.engine import DecisionEngine
from .notifiers.telegram_sender import SimpleTelegramNotifier
from .utils.report_generator import generate_final_report_text
from .utils.validators import validate_symbol_timeframe
from .analysis import (
    TechnicalIndicators, TrendAnalysis, PriceChannels,
    SupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_full_analysis_for_symbol(symbol: str, timeframe: str, fetcher: OKXDataFetcher, orchestrator: AnalysisOrchestrator, decision_engine: DecisionEngine, config: dict) -> Dict[str, Any]:
    try:
        validate_symbol_timeframe(symbol, timeframe)
        logger.info(f"--- ⏳ Analyzing {symbol} on {timeframe} ---")
        okx_symbol = symbol.replace('/', '-')
        api_timeframe = timeframe.replace('d', 'D').replace('h', 'H')
        historical_data = fetcher.fetch_historical_data(symbol=okx_symbol, timeframe=api_timeframe, days_to_fetch=365)
        if not historical_data:
            raise ConnectionError(f"Failed to fetch data for {symbol} on {timeframe}")
        df = pd.DataFrame(historical_data)
        # Standardize columns after creating DataFrame
        from .utils.data_preprocessor import standardize_dataframe_columns
        df = standardize_dataframe_columns(df)
        df.set_index('timestamp', inplace=True)

        analysis_results = orchestrator.run(df)
        recommendation = decision_engine.make_recommendation(analysis_results)
        recommendation['timeframe'] = timeframe
        recommendation['symbol'] = symbol
        return {'success': True, 'recommendation': recommendation}
    except Exception as e:
        logger.exception(f"❌ Unhandled exception during analysis of {symbol} on {timeframe}.")
        return {'success': False, 'timeframe': timeframe, 'error': f"An unexpected error occurred: {type(e).__name__}"}

def main(config, fetcher, orchestrator, decision_engine):
    parser = argparse.ArgumentParser(description='🤖 Comprehensive Technical Analysis Bot (CLI)')
    parser.add_argument('symbols', nargs='*', default=[config['trading']['DEFAULT_SYMBOL']], help='Currency symbols to analyze (e.g., BTC/USDT)')
    args = parser.parse_args()
    symbols_to_analyze = args.symbols
    notifier = SimpleTelegramNotifier(config.get('telegram', {}))

    logger.info("🚀 Starting background data services for CLI mode...")
    okx_symbols = [s.replace('/', '-') for s in symbols_to_analyze]
    fetcher.start_data_services(okx_symbols)
    logger.info("⏳ Waiting 10 seconds for initial data...")
    time.sleep(10)
    try:
        for symbol in symbols_to_analyze:
            timeframes = config['trading'].get('TIMEFRAMES_TO_ANALYZE', ['1d', '4h', '1h'])
            logger.info(f"📊 Starting analysis for {symbol} on timeframes: {timeframes}...")
            all_results = [run_full_analysis_for_symbol(symbol, tf, fetcher, orchestrator, decision_engine, config) for tf in timeframes]
            successful_recommendations = [r['recommendation'] for r in all_results if r.get('success')]
            if not successful_recommendations:
                logger.error(f"❌ All analyses failed for {symbol}. No report to generate.")
                continue
            ranked_recs = decision_engine.rank_recommendations(successful_recommendations)
            final_report = generate_final_report_text(symbol=symbol, analysis_type="تحليل شامل", ranked_results=ranked_recs)
            logger.info(f"Generated report for {symbol}:\n{final_report}")
            notifier.send(final_report, parse_mode='HTML')
            if len(symbols_to_analyze) > 1:
                time.sleep(5)
    finally:
        logger.info("⏹️ Stopping data services for CLI mode...")
        fetcher.stop()
