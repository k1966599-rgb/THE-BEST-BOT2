import os
import json
import asyncio
import logging
from typing import Dict, List

from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher
from src.data_retrieval.exceptions import APIError, NetworkError

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

async def fetch_and_save_symbol_data(
    symbol: str,
    timeframe: str,
    group: str,
    fetcher: DataFetcher,
    semaphore: asyncio.Semaphore
):
    """
    Fetches, saves, and logs data for a single symbol/timeframe combination
    while respecting the semaphore.
    """
    async with semaphore:
        logger.info(f"Fetching data for {symbol} on {timeframe}...")
        try:
            # Fetch data using the robust fetcher
            data_dict = fetcher.fetch_historical_data(symbol, timeframe, limit=1000)

            # Create directory structure, e.g., data/BTC-USDT/long_term/
            directory_path = os.path.join('data', symbol, group)
            os.makedirs(directory_path, exist_ok=True)

            # Save data to JSON file, e.g., data/BTC-USDT/long_term/1D.json
            file_path = os.path.join(directory_path, f"{timeframe}.json")
            with open(file_path, 'w') as f:
                json.dump(data_dict, f, indent=4)

            logger.info(f"✅ Successfully saved data for {symbol} on {timeframe} to {file_path}")
            return True

        except (APIError, NetworkError) as e:
            logger.error(f"❌ Failed to fetch data for {symbol} on {timeframe}: {e}")
            return False

        # A small delay to be respectful to the API, even with a semaphore
        await asyncio.sleep(0.1)

async def populate_all_data():
    """
    Concurrently iterates through the watchlist and timeframes,
    fetches the data for each, and saves it to the appropriate file.
    """
    logger.info("--- Starting Concurrent Data Population ---")

    config = get_config()
    fetcher = DataFetcher(config)

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    # Set concurrency limit to avoid API rate limiting
    concurrency_limit = config.get('trading', {}).get('CONCURRENCY_LIMIT', 5)
    semaphore = asyncio.Semaphore(concurrency_limit)
    logger.info(f"Concurrency limit set to {concurrency_limit}")

    # Create a reverse map to find the group for a given timeframe
    tf_to_group = {tf: group for group, tfs in timeframe_groups.items() for tf in tfs}

    tasks = []
    for symbol in watchlist:
        for timeframe in timeframes:
            group = tf_to_group.get(timeframe)
            if not group:
                logger.warning(f"Timeframe {timeframe} does not belong to any group. Skipping.")
                continue

            # Create a task for each fetch operation
            task = fetch_and_save_symbol_data(symbol, timeframe, group, fetcher, semaphore)
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
    # To run this script, execute `python populate_data.py` in your terminal
    asyncio.run(populate_all_data())