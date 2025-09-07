import sys
import os
import argparse
from datetime import datetime
import time
import copy
import traceback
import concurrent.futures
from typing import List, Optional
import threading
import logging

# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_bot import ComprehensiveTradingBot
from config import get_config, WATCHLIST
from telegram_sender import send_telegram_message
from report_generator import generate_final_report_text
from okx_data import OKXDataFetcher, validate_symbol_timeframe

def run_analysis_for_timeframe(symbol: str, timeframe: str, config: dict, okx_fetcher: OKXDataFetcher) -> dict:
    """Runs the complete analysis for a single symbol on a specific timeframe."""
    try:
        # First, validate if the timeframe is supported for the symbol
        validate_symbol_timeframe(symbol, timeframe)

        logger.info(f"--- ⏳ Analyzing {symbol} on {timeframe} ---")
        timeframe_config = copy.deepcopy(config)
        timeframe_config['trading']['INTERVAL'] = timeframe
        
        bot = ComprehensiveTradingBot(symbol=symbol, timeframe=timeframe, config=timeframe_config, okx_fetcher=okx_fetcher)
        bot.run_complete_analysis()
        bot.final_recommendation['timeframe'] = timeframe
        return {'success': True, 'bot': bot}
    except Exception as e:
        error_message = f"❌ Exception during analysis of {symbol} on {timeframe}. Error: {type(e).__name__}: {str(e)}"
        logger.error(error_message)
        # We don't print the full traceback for validation errors as they are expected.
        if not isinstance(e, ValueError):
            # Using logger.exception will automatically include traceback info
            logger.exception(f"Full traceback for error in {symbol} on {timeframe}:")
        return {'success': False, 'timeframe': timeframe, 'error': error_message}

def rank_opportunities(results: list) -> list:
    """
    Ranks analysis results from different timeframes, prioritizing actionable signals
    over "Wait" signals.
    """
    for res in results:
        if res.get('success'):
            rec = res['bot'].final_recommendation
            # Give a significant penalty to "Wait" signals to push them down the ranking
            signal_multiplier = 0.1 if 'انتظار' in rec.get('main_action', '') else 1.0

            # Add a small bonus for divergences, as they are strong signals
            divergence_bonus = 1.0
            indicators_analysis = res.get('bot', {}).analysis_results.get('indicators', {})
            if indicators_analysis.get('rsi_divergence') or indicators_analysis.get('macd_divergence'):
                divergence_bonus = 1.2 # 20% bonus to the score if a divergence is found

            rank_score = abs(rec.get('total_score', 0)) * (rec.get('confidence', 0) / 100) * signal_multiplier * divergence_bonus
            res['rank_score'] = rank_score
        else:
            res['rank_score'] = -1
    return sorted(results, key=lambda x: x.get('rank_score', -1), reverse=True)

def get_top_20_symbols(okx_fetcher: OKXDataFetcher) -> List[str]:
    """Fetches all tickers and returns the top 20 by USDT volume."""
    # This functionality is simplified as the main focus is the bot's analysis engine.
    logger.info("Fetching market tickers to determine top 20 by volume...")
    # In a real scenario, this would involve a call to okx_fetcher
    return WATCHLIST

def get_ranked_analysis_for_symbol(symbol: str, config: dict, okx_fetcher: OKXDataFetcher, timeframes_to_analyze: Optional[List[str]] = None, analysis_type: str = "تحليل مخصص") -> str:
    """
    Performs multi-timeframe analysis in parallel and returns a single, formatted report string.
    """
    if timeframes_to_analyze:
        timeframes = timeframes_to_analyze
    else:
        timeframes = config['trading'].get('TIMEFRAMES_TO_ANALYZE', ['1d'])

    logger.info(f"📊 Starting PARALLEL analysis for {symbol} on {len(timeframes)} timeframes: {timeframes}...")

    all_timeframe_results = []
    # Limit max_workers to a reasonable number to avoid resource exhaustion and API rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_tf = {executor.submit(run_analysis_for_timeframe, symbol, tf, config, okx_fetcher): tf for tf in timeframes}
        for future in concurrent.futures.as_completed(future_to_tf):
            tf = future_to_tf[future]
            try:
                result = future.result()
                all_timeframe_results.append(result)
            except Exception as exc:
                logger.error(f'❌ Timeframe {tf} for {symbol} generated an exception in the main loop: {exc}')
                # Optionally, append a failure result to still show it in the report
                all_timeframe_results.append({'success': False, 'timeframe': tf, 'error': str(exc)})

    # Check if all analyses failed
    if not any(r.get('success') for r in all_timeframe_results):
        return f"❌ تعذر تحليل {symbol} لجميع الأطر الزمنية المطلوبة."

    # Rank all results (failures will be ranked last)
    ranked_results = rank_opportunities(all_timeframe_results)

    final_report = generate_final_report_text(
        symbol=symbol,
        analysis_type=analysis_type,
        ranked_results=ranked_results
    )
    return final_report

def _setup_analysis_parameters(config: dict) -> tuple:
    """Parses command-line arguments to determine analysis parameters."""
    parser = argparse.ArgumentParser(description='🤖 Comprehensive Technical Analysis Bot (CLI)')
    parser.add_argument('symbols', nargs='*', help='Currency symbols to analyze (e.g., BTC/USDT)')
    parser.add_argument('--watchlist', action='store_true', help='Analyze the default watchlist')

    analysis_group = parser.add_mutually_exclusive_group()
    analysis_group.add_argument('--long', action='store_true', help='Run long-term analysis')
    analysis_group.add_argument('--medium', action='store_true', help='Run medium-term analysis')
    analysis_group.add_argument('--short', action='store_true', help='Run short-term analysis')

    args = parser.parse_args()

    timeframe_groups = config['trading']['TIMEFRAME_GROUPS']
    if args.long:
        analysis_type = "استثمار طويل المدى (1D - 4H - 1H)"
        timeframes = timeframe_groups['long']
    elif args.medium:
        analysis_type = "تداول متوسط المدى (30m - 15m)"
        timeframes = timeframe_groups['medium']
    elif args.short:
        analysis_type = "مضاربة سريعة (5m - 3m)"
        timeframes = timeframe_groups['short']
    else:
        analysis_type = "تحليل افتراضي"
        timeframes = config['trading']['TIMEFRAMES_TO_ANALYZE']

    symbols_to_analyze = args.symbols if args.symbols else WATCHLIST if args.watchlist else [config['trading']['DEFAULT_SYMBOL']]

    return symbols_to_analyze, timeframes, analysis_type

def main():
    """Main function to run the bot."""
    config = get_config()
    symbols_to_analyze, timeframes, analysis_type = _setup_analysis_parameters(config)

    logger.info("🚀 Initializing OKX Data Fetcher...")
    okx_fetcher = OKXDataFetcher()
    okx_symbols = [s.replace('/', '-') for s in symbols_to_analyze]
    okx_fetcher.start_data_services(okx_symbols)

    logger.info("⏳ Waiting 10 seconds for initial data...")
    time.sleep(10)

    try:
        for symbol in symbols_to_analyze:
            final_report = get_ranked_analysis_for_symbol(symbol, config, okx_fetcher, timeframes, analysis_type)
            logger.info(f"Generated report for {symbol}:\n{final_report}")
            send_telegram_message(final_report)
            if len(symbols_to_analyze) > 1:
                time.sleep(5)
    finally:
        logger.info("⏹️ Stopping OKX Data Fetcher...")
        okx_fetcher.stop()

if __name__ == "__main__":
    main()
