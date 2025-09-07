import argparse
import time
import logging
from typing import List, Dict, Any

from .config import get_config, WATCHLIST
from .data.okx_fetcher import OKXDataFetcher
from .analysis.orchestrator import AnalysisOrchestrator
from .decision_engine.engine import DecisionEngine
from .notifiers.telegram_sender import SimpleTelegramNotifier
from .utils.report_generator import generate_final_report_text
from .utils.validators import validate_symbol_timeframe

# Import all analysis modules to be used
from .analysis.trends import TrendAnalysis
from .analysis.technical_score import TechnicalIndicators
from .analysis.trend_lines import TrendLineAnalysis
from .analysis.channels import PriceChannels
from .analysis.support_resistance import SupportResistanceAnalysis
from .analysis.fibonacci import FibonacciAnalysis
from .analysis.classic_patterns import ClassicPatterns

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_full_analysis_for_symbol(symbol: str, timeframe: str, fetcher: OKXDataFetcher, orchestrator: AnalysisOrchestrator, decision_engine: DecisionEngine, config: dict) -> Dict[str, Any]:
    """
    Runs the complete, refactored analysis and decision pipeline for a single symbol and timeframe.
    """
    try:
        validate_symbol_timeframe(symbol, timeframe)
        logger.info(f"--- ⏳ Analyzing {symbol} on {timeframe} ---")

        # 1. Fetch Data
        okx_symbol = symbol.replace('/', '-')
        api_timeframe = timeframe.replace('d', 'D').replace('h', 'H')
        # This part needs a better way to calculate lookback, for now, use a large fixed value
        df = fetcher.fetch_historical_data(symbol=okx_symbol, timeframe=api_timeframe, days_to_fetch=365)

        if not df:
            raise ConnectionError(f"Failed to fetch data for {symbol} on {timeframe}")

        # 2. Run Analysis
        analysis_results = orchestrator.run(df)

        # 3. Make Recommendation
        recommendation = decision_engine.make_recommendation(analysis_results)
        recommendation['timeframe'] = timeframe # Add timeframe for context
        recommendation['symbol'] = symbol

        return {'success': True, 'recommendation': recommendation}

    except (ValueError, ConnectionError) as e:
        logger.warning(f"Analysis failed for {symbol} on {timeframe}: {e}")
        return {'success': False, 'timeframe': timeframe, 'error': str(e)}
    except Exception as e:
        logger.exception(f"❌ Unhandled exception during analysis of {symbol} on {timeframe}.")
        return {'success': False, 'timeframe': timeframe, 'error': f"An unexpected error occurred: {type(e).__name__}"}

def main(config, fetcher, orchestrator, decision_engine):
    """
    Main function to run the bot in CLI mode.
    It takes pre-initialized components as arguments.
    """
    # --- Setup Command-line Arguments ---
    parser = argparse.ArgumentParser(description='🤖 Comprehensive Technical Analysis Bot (CLI)')
    parser.add_argument('symbols', nargs='*', default=[config['trading']['DEFAULT_SYMBOL']], help='Currency symbols to analyze (e.g., BTC/USDT)')
    args = parser.parse_args()
    symbols_to_analyze = args.symbols

    # --- Initialize Notifier ---
    # The notifier is specific to this app mode
    notifier = SimpleTelegramNotifier(config.get('telegram', {}))

    # --- Start Data Services ---
    logger.info("🚀 Starting background data services for CLI mode...")
    okx_symbols = [s.replace('/', '-') for s in symbols_to_analyze]
    fetcher.start_data_services(okx_symbols)
    logger.info("⏳ Waiting 10 seconds for initial data...")
    time.sleep(10)

    try:
        # --- Main Application Loop ---
        for symbol in symbols_to_analyze:
            timeframes = config['trading'].get('TIMEFRAMES_TO_ANALYZE', ['1d', '4h', '1h'])
            logger.info(f"📊 Starting analysis for {symbol} on timeframes: {timeframes}...")

            all_results = []
            for tf in timeframes:
                # This part can be parallelized again later
                result = run_full_analysis_for_symbol(symbol, tf, fetcher, orchestrator, decision_engine, config)
                all_results.append(result)

            successful_recommendations = [r['recommendation'] for r in all_results if r.get('success')]

            if not successful_recommendations:
                logger.error(f"❌ All analyses failed for {symbol}. No report to generate.")
                continue

            # Rank the successful recommendations
            ranked_recs = decision_engine.rank_recommendations(successful_recommendations)

            # Generate and send the final report
            # Note: The report generator will likely need to be adapted to this new `ranked_recs` format
            final_report = generate_final_report_text(
                symbol=symbol,
                analysis_type="تحليل شامل",
                ranked_results=ranked_recs
            )

            logger.info(f"Generated report for {symbol}:\n{final_report}")
            notifier.send(final_report, parse_mode='HTML')

            if len(symbols_to_analyze) > 1:
                time.sleep(5)
    finally:
        logger.info("⏹️ Stopping data services for CLI mode...")
        fetcher.stop()
