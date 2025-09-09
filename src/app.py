"""
This module contains the command-line interface for the trading bot.
"""
import argparse
import time
import logging
from typing import Dict, Any
import pandas as pd

from .data.okx_fetcher import OKXDataFetcher
from .analysis.orchestrator import AnalysisOrchestrator
from .decision_engine.engine import DecisionEngine
from .notifiers.telegram_sender import SimpleTelegramNotifier
from .reporting.report_builder import ReportBuilder
from .utils.validators import validate_symbol_timeframe
from .utils.data_preprocessor import standardize_dataframe_columns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_full_analysis_for_symbol(
    symbol: str,
    timeframe: str,
    fetcher: OKXDataFetcher,
    orchestrator: AnalysisOrchestrator,
    decision_engine: DecisionEngine
) -> Dict[str, Any]:
    """
    Runs a full analysis for a given symbol and timeframe.
    """
    try:
        validate_symbol_timeframe(symbol, timeframe)
        logger.info("--- ⏳ Analyzing %s on %s ---", symbol, timeframe)
        okx_symbol = symbol.replace('/', '-')
        api_timeframe = timeframe.replace('d', 'D').replace('h', 'H')
        historical_data = fetcher.fetch_historical_data(
            symbol=okx_symbol,
            timeframe=api_timeframe,
            days_to_fetch=365
        )
        if not historical_data:
            raise ConnectionError(
                f"Failed to fetch data for {symbol} on {timeframe}"
            )
        df = pd.DataFrame(historical_data)
        df = standardize_dataframe_columns(df)
        df.set_index('timestamp', inplace=True)

        analysis_results = orchestrator.run(df)
        recommendation = decision_engine.make_recommendation(analysis_results, df, symbol, timeframe)
        recommendation['timeframe'] = timeframe
        recommendation['symbol'] = symbol
        return {'success': True, 'recommendation': recommendation}
    except ConnectionError as e:
        logger.error("Connection error during analysis of %s on %s: %s", symbol, timeframe, e)
        return {'success': False, 'timeframe': timeframe, 'error': str(e)}
    except Exception as e:
        logger.exception(
            "❌ Unhandled exception during analysis of %s on %s.",
            symbol,
            timeframe
        )
        return {
            'success': False,
            'timeframe': timeframe,
            'error': f"An unexpected error occurred: {e}"
        }

def main(config, fetcher, orchestrator, decision_engine):
    """
    The main function for the CLI mode.
    """
    parser = argparse.ArgumentParser(
        description='🤖 Comprehensive Technical Analysis Bot (CLI)'
    )
    parser.add_argument(
        'symbols',
        nargs='*',
        default=[config['trading']['DEFAULT_SYMBOL']],
        help='Currency symbols to analyze (e.g., BTC/USDT)'
    )
    symbols_to_analyze = parser.parse_args().symbols
    components = {
        'notifier': SimpleTelegramNotifier(config.get('telegram', {})),
        'report_builder': ReportBuilder(config)
    }

    logger.info("🚀 Starting background data services for CLI mode...")
    okx_symbols = [s.replace('/', '-') for s in symbols_to_analyze]
    fetcher.start_data_services(okx_symbols)
    logger.info("⏳ Waiting 10 seconds for initial data...")
    time.sleep(10)
    try:
        for symbol in symbols_to_analyze:
            timeframes = config['trading'].get('TIMEFRAMES_TO_ANALYZE', ['1d', '4h', '1h'])
            logger.info(
                "📊 Starting analysis for %s on timeframes: %s...",
                symbol,
                timeframes
            )
            all_results = [
                run_full_analysis_for_symbol(
                    symbol, tf, fetcher, orchestrator, decision_engine
                )
                for tf in timeframes
            ]
            successful_recommendations = [
                r['recommendation'] for r in all_results if r.get('success')
            ]
            if not successful_recommendations:
                logger.error(
                    "❌ All analyses failed for %s. No report to generate.",
                    symbol
                )
                continue
            ranked_recs = decision_engine.rank_recommendations(
                successful_recommendations
            )

            last_price = fetcher.get_cached_price(symbol.replace('/', '-')) or {}
            general_info = {
                'symbol': symbol,
                'analysis_type': "تحليل شامل",
                'current_price': last_price.get('price', 0)
            }
            final_report = components['report_builder'].build_report(
                ranked_results=ranked_recs,
                general_info=general_info
            )
            logger.info("Generated report for %s:\n%s", symbol, final_report)
            components['notifier'].send(final_report, parse_mode='HTML')
            if len(symbols_to_analyze) > 1:
                time.sleep(5)
    finally:
        logger.info("⏹️ Stopping data services for CLI mode...")
        fetcher.stop()
