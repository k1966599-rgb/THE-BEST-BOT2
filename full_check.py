import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import List, Dict

# Add src to path to import project modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.settings import AppSettings
    from src.data_retrieval.data_fetcher import DataFetcher
    from src.data_retrieval.exceptions import APIError, NetworkError
    from src.strategies.exceptions import InsufficientDataError
    from src.strategies.fibo_analyzer import FiboAnalyzer
except ImportError as e:
    print(f"❌ FAILED to import necessary modules. Error: {e}")
    sys.exit(1)

# --- Main Check Logic ---

async def check_pair_timeframe(symbol: str, timeframe: str, config: Dict) -> Dict:
    """
    Performs a full analysis check for a single symbol-timeframe pair.
    """
    print(f"▶️  Checking: {symbol} on {timeframe}...")

    try:
        # 1. Initialize Fetcher and Analyzer for each check
        fetcher = DataFetcher(config)
        analyzer = FiboAnalyzer(config=config, fetcher=fetcher, timeframe=timeframe)

        # 2. Fetch Data
        candle_limit = config.get("trading", {}).get("CANDLE_FETCH_LIMITS", {}).get(timeframe, 1000)
        data_dict = await asyncio.to_thread(fetcher.fetch_historical_data, symbol, timeframe, limit=candle_limit)

        # 3. Run Analysis
        df = pd.DataFrame(data_dict['data'])
        analysis_result = await asyncio.to_thread(analyzer.get_analysis, df, symbol, timeframe)

        if analysis_result.get("signal"):
            return {"status": "✅ SUCCESS", "details": f"Signal: {analysis_result['signal']}"}
        else:
            return {"status": "❌ FAILED", "details": "Analysis completed but no signal was generated."}

    except InsufficientDataError as e:
        return {"status": "❌ FAILED", "details": f"Insufficient Data: {e}"}
    except APIError as e:
        return {"status": "❌ FAILED", "details": f"API Error: {e}"}
    except NetworkError as e:
        return {"status": "❌ FAILED", "details": f"Network Error: {e}"}
    except Exception as e:
        return {"status": "❌ FAILED", "details": f"Unexpected Error: {type(e).__name__} - {e}"}


async def main():
    """
    Main function to run the comprehensive check.
    """
    print("--- Starting Comprehensive Analysis Check ---")

    # Load settings using the centralized config getter
    try:
        from src.config import get_config
        config = get_config()
        print("✅ Configuration loaded successfully.")
    except Exception as e:
        print(f"FATAL: Could not load configuration via get_config(). Error: {e}")
        return

    watchlist = config.get("trading", {}).get("WATCHLIST", [])
    all_timeframes = []
    for group in config.get("trading", {}).get("TIMEFRAME_GROUPS", {}).values():
        all_timeframes.extend(group)

    results: Dict[str, Dict[str, Dict]] = {symbol: {} for symbol in watchlist}

    total_checks = len(watchlist) * len(all_timeframes)
    completed_checks = 0

    for symbol in watchlist:
        print(f"\n--- Processing Symbol: {symbol} ---")
        for timeframe in all_timeframes:
            result = await check_pair_timeframe(symbol, timeframe, config)
            results[symbol][timeframe] = result
            completed_checks += 1
            print(f"   Result: {result['status']} - {result['details']}")
            print(f"   Progress: {completed_checks}/{total_checks}")

    # --- Print Final Report ---
    print("\n\n===========================================")
    print("      COMPREHENSIVE CHECK REPORT")
    print("===========================================")

    success_count = 0
    failed_combinations = []

    for symbol, timeframes in results.items():
        print(f"\n--- Results for {symbol} ---")
        for timeframe, result in timeframes.items():
            print(f"  - {timeframe.ljust(5)}: {result['status']} - {result['details']}")
            if result['status'] == "✅ SUCCESS":
                success_count += 1
            else:
                failed_combinations.append(f"{symbol} @ {timeframe}: {result['details']}")

    print("\n--- SUMMARY ---")
    print(f"Total Checks: {total_checks}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed:     {len(failed_combinations)}")

    if failed_combinations:
        print("\n--- FAILED COMBINATIONS ---")
        for failure in failed_combinations:
            print(f"- {failure}")

if __name__ == "__main__":
    # Load .env file
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print("⚠️  Warning: .env file not found. Script will rely on environment variables.")

    # Add pandas import here for the main guard
    import pandas as pd
    asyncio.run(main())