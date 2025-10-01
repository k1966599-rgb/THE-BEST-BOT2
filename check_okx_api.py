import json
import pprint
from src.config import get_config
import okx.MarketData as MarketData

def run_okx_api_check():
    """
    Performs a direct, isolated check of the OKX API to diagnose connection
    and data retrieval issues.
    """
    print("--- Starting OKX API Diagnostic Check ---")

    try:
        # 1. Load configuration
        print("1. Loading configuration from .env file...")
        config = get_config()
        exchange_config = config.get('exchange', {})
        api_key = exchange_config.get('API_KEY')
        api_secret = exchange_config.get('API_SECRET')
        api_password = exchange_config.get('PASSWORD')
        sandbox_mode = exchange_config.get('SANDBOX_MODE', True)

        if not all([api_key, api_secret, api_password]):
            print("\n❌ FATAL: API Key, Secret, or Password not found in configuration.")
            return

        print("   - Configuration loaded successfully.")

        # 2. Initialize OKX MarketAPI client
        flag = "1" if sandbox_mode else "0"
        print(f"2. Initializing OKX MarketAPI client (Sandbox Mode: {sandbox_mode}, Flag: '{flag}')...")

        market_api = MarketData.MarketAPI(
            api_key=api_key,
            api_secret_key=api_secret,
            passphrase=api_password,
            use_server_time=False,
            flag=flag,
            debug=True # Enable full debug output from the library
        )
        print("   - OKX client initialized.")

        # 3. Attempt to fetch data
        symbol = 'BTC-USDT'
        timeframe = '1H'
        limit = '10' # Request just a few candles for a quick check
        print(f"\n3. Attempting to fetch historical data for '{symbol}' on timeframe '{timeframe}' with limit {limit}...")

        # The actual API call
        result = market_api.get_history_candlesticks(
            instId=symbol,
            bar=timeframe,
            limit=limit
        )

        # 4. Print the raw result from the API
        print("\n--- RAW API RESPONSE ---")
        pprint.pprint(result)
        print("------------------------\n")

        # 5. Analyze the result
        print("--- ANALYSIS OF RESPONSE ---")
        if isinstance(result, dict):
            code = result.get('code')
            msg = result.get('msg', 'No message in response.')
            data = result.get('data', [])

            if code == '0':
                print(f"✅ Success! API returned code '0'.")
                if data:
                    print(f"   - Received {len(data)} candle(s). Data appears to be flowing correctly.")
                    print("   - First candle received:")
                    pprint.pprint(data[0])
                else:
                    print("   - WARNING: API call was successful, but no data was returned. This might be normal if the market is new or has no recent trades.")
            else:
                print(f"❌ ERROR: API returned a non-zero code: '{code}'.")
                print(f"   - Message: {msg}")
                print(f"   - This indicates a problem with the request or your account (e.g., invalid API key, permissions issue).")

        else:
            print("❌ UNEXPECTED RESPONSE: The response from the API was not a dictionary as expected.")
            print("   - This could indicate a network issue or a change in the OKX API.")

    except Exception as e:
        print(f"\n❌ A CRITICAL EXCEPTION OCCURRED ---")
        print(f"   - Exception Type: {type(e).__name__}")
        print(f"   - Exception Details: {e}")
        import traceback
        traceback.print_exc()
        print("\n   - This type of error often points to a problem with network connectivity, SSL certificates, or a bug in the client library.")

    finally:
        print("\n--- Diagnostic Check Finished ---")


if __name__ == '__main__':
    run_okx_api_check()