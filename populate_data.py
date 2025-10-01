import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher
from src.data_retrieval.exceptions import APIError, NetworkError
from src.utils.symbol_util import normalize_symbol
from src.cache_manager import CacheManager

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

async def fetch_and_save_symbol_data(
    symbol: str,
    timeframe: str,
    fetcher: DataFetcher,
    cache_manager: CacheManager,
    semaphore: asyncio.Semaphore,
    limit: int,
):
    """
    Fetches data for a single symbol/timeframe and saves it via the CacheManager.
    """
    async with semaphore:
        logger.info(f"Fetching data for {symbol} on {timeframe} with limit {limit}...")
        try:
            # fetch_historical_data is a synchronous function
            data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=limit)

            # The data_dict from fetcher is {"symbol": symbol, "data": list_of_dicts}
            if data_dict and data_dict.get("data"):
                # Use the CacheManager to save the data.
                cache_manager.set(symbol, timeframe, data_dict["data"])
                return True
            else:
                logger.warning(f"No data returned from fetcher for {symbol} on {timeframe}. Skipping save.")
                return False

        except (APIError, NetworkError) as e:
            logger.error(f"❌ Failed to fetch data for {symbol} on {timeframe}: {e}")
            return False
        finally:
            # A small delay to be respectful to the API, even with a semaphore
            await asyncio.sleep(0.1)


async def populate_all_data():
    """
    Concurrently iterates through the watchlist and timeframes,
    fetches the data for each, and saves it to the cache via the CacheManager.
    """
    logger.info("--- Starting Concurrent Data Population ---")

    config = get_config()
    fetcher = DataFetcher(config)
    cache_manager = CacheManager()

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    # Correctly gather all unique timeframes from the groups
    all_timeframes = sorted(list(set(tf for group in timeframe_groups.values() for tf in group)))

    logger.info(f"Found timeframes to populate: {all_timeframes}")

    # Set concurrency limit to avoid API rate limiting
    concurrency_limit = config.get('trading', {}).get('CONCURRENCY_LIMIT', 5)
    semaphore = asyncio.Semaphore(concurrency_limit)
    logger.info(f"Concurrency limit set to {concurrency_limit}")

    # Get candle limits from config
    candle_limits = config.get('trading', {}).get('CANDLE_FETCH_LIMITS', {})
    default_limit = candle_limits.get('default', 1000)

    tasks = []
    for display_symbol in watchlist:
        normalized_symbol = normalize_symbol(display_symbol)
        for timeframe in all_timeframes:
            # Determine the correct limit for the timeframe
            limit = candle_limits.get(timeframe, default_limit)

            # Create a task for each fetch operation
            task = fetch_and_save_symbol_data(
                normalized_symbol, timeframe, fetcher, cache_manager, semaphore, limit
            )
            tasks.append(task)

    if not tasks:
        logger.warning("No data population tasks were created. Check your config.")
        return

    logger.info(f"Created {len(tasks)} data fetching tasks. Starting execution...")

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)

    successful_tasks = sum(1 for r in results if r)
    failed_tasks = len(results) - successful_tasks

    logger.info("--- Data Population Complete ---")
    logger.info(f"Summary: {successful_tasks} tasks succeeded, {failed_tasks} tasks failed.")

if __name__ == "__main__":
    # To run this script, execute `python populate_data.py` from the project root.
    # The following lines ensure that the 'src' module can be found.
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    # --- Comprehensive logging setup ---
    # 1. Create a new log file for this run, clearing the old one.
    LOG_FILE = 'population.log'
    with open(LOG_FILE, 'w') as f:
        f.write("--- Starting new data population log ---\n")

    # 2. Configure a file handler to log everything (INFO and above)
    file_handler = logging.FileHandler(LOG_FILE)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # 3. Get the root logger, clear existing handlers, and add our new file handler
    # This ensures that only our desired logs go to the file.
    root_logger = logging.getLogger()
    # Clear any handlers configured by basicConfig or previous runs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO) # Set root logger level

    # Also, let's keep console output clean for the user
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    try:
        root_logger.info("--- Script execution started ---")
        asyncio.run(populate_all_data())
        root_logger.info("--- Script execution finished without fatal errors ---")

    except Exception as e:
        # Log the full exception traceback to the file and console
        root_logger.critical(f"A critical, unhandled exception occurred: {e}", exc_info=True)
        print(f"\n❌ A critical error occurred. Please check 'population.log' for the full traceback.")