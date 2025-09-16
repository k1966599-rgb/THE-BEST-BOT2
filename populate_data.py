import os
import json
import time
import asyncio
from src.config import get_config
from src.data_retrieval.data_fetcher import DataFetcher

async def populate_all_data():
    """
    Iterates through the watchlist and timeframes in the config,
    fetches the data for each, and saves it to the appropriate file.
    """
    print("--- Starting Data Population ---")

    config = get_config()
    fetcher = DataFetcher(config)

    watchlist = config.get('trading', {}).get('WATCHLIST', [])
    timeframes = config.get('trading', {}).get('TIMEFRAMES', [])
    timeframe_groups = config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

    # Create a reverse map to find the group for a given timeframe
    tf_to_group = {tf: group for group, tfs in timeframe_groups.items() for tf in tfs}

    for symbol in watchlist:
        print(f"\nFetching data for symbol: {symbol}")
        for timeframe in timeframes:
            # Determine the correct subdirectory (long_term, medium_term, etc.)
            group = tf_to_group.get(timeframe)
            if not group:
                print(f"  - Warning: Timeframe {timeframe} does not belong to any group. Skipping.")
                continue

            # --- Fetch data ---
            print(f"  - Fetching {timeframe} data...")
            data_dict = fetcher.fetch_historical_data(symbol, timeframe)

            if data_dict and data_dict.get('data'):
                # --- Create directory structure ---
                # e.g., data/BTC-USDT/long_term/
                directory_path = os.path.join('data', symbol, group)
                os.makedirs(directory_path, exist_ok=True)

                # --- Save data to JSON file ---
                # e.g., data/BTC-USDT/long_term/1D.json
                file_path = os.path.join(directory_path, f"{timeframe}.json")

                with open(file_path, 'w') as f:
                    json.dump(data_dict, f, indent=4)

                print(f"    ✅ Saved to {file_path}")
            else:
                print(f"    ❌ Failed to fetch data for {symbol} on {timeframe}.")

            # Be respectful to the API rate limits
            await asyncio.sleep(1) # 1-second delay between requests

    print("\n--- Data Population Complete ---")

if __name__ == "__main__":
    asyncio.run(populate_all_data())
