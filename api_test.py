import os
import sys
from dotenv import load_dotenv

# Add src to path to import project modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

print("--- API Connection Test Script ---")

try:
    from config import get_config
    from data_retrieval.data_fetcher import DataFetcher
    from data_retrieval.exceptions import APIError, NetworkError
    print("✅ [1/4] Imports successful.")
except ImportError as e:
    print(f"❌ [1/4] FAILED: Could not import necessary modules.")
    print(f"   Error: {e}")
    print("   Please ensure you are in the root project directory.")
    sys.exit(1)

def run_api_test():
    """Runs a direct test on the DataFetcher to diagnose API issues."""
    print("\n▶️  [2/4] Loading configuration from .env file...")

    try:
        config = get_config()
        # Check if essential API keys are loaded
        if not all([config.get('exchange', {}).get(k) for k in ['API_KEY', 'API_SECRET', 'PASSWORD']]):
             print("⚠️  Warning: One or more API credentials (KEY, SECRET, PASSWORD) are missing from the config.")
        print("✅ [2/4] Configuration loaded.")
    except Exception as e:
        print(f"❌ [2/4] FAILED: Could not load configuration.")
        print(f"   Error: {e}")
        sys.exit(1)

    print("\n▶️  [3/4] Initializing DataFetcher...")
    try:
        fetcher = DataFetcher(config)
        print("✅ [3/4] DataFetcher initialized.")
    except Exception as e:
        print(f"❌ [3/4] FAILED: Could not initialize DataFetcher.")
        print(f"   Error: {e}")
        sys.exit(1)

    print("\n▶️  [4/4] Attempting to fetch data for BTC/USDT from OKX...")
    try:
        data = fetcher.fetch_historical_data('BTC/USDT', '1D', limit=10)

        if data and data.get('data'):
            print("\n=====================================================")
            print("✅ SUCCESS: Data fetched successfully!")
            print("=====================================================")
            print(f"   - Fetched {len(data['data'])} candles.")
            print(f"   - Latest candle timestamp: {data['data'][-1]['timestamp']}")
            print("\n   CONCLUSION: Your API Key and connection are working correctly.")
        else:
            print("\n=====================================================")
            print("❌ FAILURE: API call succeeded but returned NO DATA.")
            print("=====================================================")
            print("\n   CONCLUSION: This might indicate an issue with the specific symbol or exchange status.")

    except (APIError, NetworkError) as e:
        print("\n=====================================================")
        print("❌ FAILURE: The API call failed with an error.")
        print("=====================================================")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {e}")
        print("\n   CONCLUSION: This is likely an issue with your API Key, Secret, or Passphrase.")
        print("   RECOMMENDATION: Please double-check your credentials in the .env file.")
    except Exception as e:
        print("\n=====================================================")
        print("❌ FAILURE: An unexpected script error occurred.")
        print("=====================================================")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {e}")

if __name__ == "__main__":
    # Ensure the .env file is loaded from the correct path
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print("⚠️  Warning: .env file not found. Script will rely on environment variables.")

    run_api_test()