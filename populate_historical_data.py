import logging
import time
import argparse
from src.config import get_config
from src.data.okx_fetcher import OKXDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(symbol_to_fetch: str = None, timeframe_to_fetch: str = None):
    """
    Main function to populate historical data.
    Can fetch for a specific symbol/timeframe or all combinations in the watchlist.
    """
    logger.info("--- 🚀 Starting Historical Data Population ---")

    config = get_config()
    fetcher = OKXDataFetcher(config)

    if symbol_to_fetch:
        watchlist = [symbol_to_fetch]
        logger.info(f"🎯 Targeting specific symbol: {symbol_to_fetch}")
    else:
        watchlist = config.get('trading', {}).get('WATCHLIST', [])
        logger.info("🎯 Processing all symbols in watchlist.")

    if timeframe_to_fetch:
        timeframes_to_analyze = [timeframe_to_fetch]
        logger.info(f"🎯 Targeting specific timeframe: {timeframe_to_fetch}")
    else:
        timeframes_to_analyze = config.get('trading', {}).get('TIMEFRAMES_TO_ANALYZE', [])
        logger.info("🎯 Processing all timeframes in config.")

    if not watchlist or not timeframes_to_analyze:
        logger.error("❌ Watchlist or timeframes_to_analyze not found in config. Aborting.")
        return

    logger.info(f"🔍 Found {len(watchlist)} symbols and {len(timeframes_to_analyze)} timeframes to process.")

    total_fetches = len(watchlist) * len(timeframes_to_analyze)
    current_fetch = 0

    for symbol in watchlist:
        okx_symbol = symbol.replace('/', '-')
        for timeframe in timeframes_to_analyze:
            current_fetch += 1
            logger.info(f"--- ({current_fetch}/{total_fetches}) Fetching data for {symbol} on {timeframe} timeframe ---")
            try:
                data = fetcher.fetch_historical_data(symbol=okx_symbol, timeframe=timeframe)
                if data and data.get('data'):
                    logger.info(f"✅ Successfully fetched and stored {len(data['data'])} candles for {symbol} ({timeframe}).")
                else:
                    logger.warning(f"⚠️ No data returned for {symbol} ({timeframe}). It might not be available on the exchange.")

                time.sleep(1)
            except Exception as e:
                logger.exception(f"❌ An unexpected error occurred while fetching data for {symbol} ({timeframe}).")

    logger.info("--- ✅ Historical Data Population Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Populate historical data for crypto symbols.')
    parser.add_argument(
        '--symbol',
        type=str,
        help='A specific symbol to fetch (e.g., BTC/USDT). If not provided, all symbols in the watchlist will be fetched.'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        help='A specific timeframe to fetch (e.g., 1D). If not provided, all timeframes in the config will be fetched.'
    )
    args = parser.parse_args()

    main(symbol_to_fetch=args.symbol, timeframe_to_fetch=args.timeframe)
