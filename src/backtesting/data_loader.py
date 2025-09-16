import pandas as pd
import json
import os
from typing import Optional, Dict, List, Any

# This configuration can be moved to a central config file later if needed
TIMEFRAME_GROUPS: Dict[str, List[str]] = {
    "long_term": ['1D', '4H', '1H'],
    "medium_term": ['30m', '15m'],
    "short_term": ['5m', '3m']
}

def load_backtest_data(symbol: str, timeframe: str, data_dir: str = 'data') -> Optional[pd.DataFrame]:
    """
    Loads historical data for a specific symbol and timeframe from local JSON files.

    Args:
        symbol (str): The trading symbol (e.g., 'BTC-USDT').
        timeframe (str): The timeframe for the data (e.g., '4H').
        data_dir (str): The root directory where data is stored.

    Returns:
        Optional[pd.DataFrame]: A pandas DataFrame with the historical data,
                                indexed by timestamp, or None if loading fails.
    """
    group = None
    for g, tfs in TIMEFRAME_GROUPS.items():
        if timeframe in tfs:
            group = g
            break

    if not group:
        print(f"Error: Timeframe '{timeframe}' is not defined in any group.")
        return None

    file_path = os.path.join(data_dir, symbol, group, f"{timeframe}.json")

    if not os.path.exists(file_path):
        print(f"Error: Data file not found at '{file_path}'. Please run populate_data.py first.")
        return None

    try:
        with open(file_path, 'r') as f:
            data_dict = json.load(f)
            df = pd.DataFrame(data_dict.get('data', []))

            if df.empty:
                print(f"Warning: Data file '{file_path}' is empty.")
                return df

            # Convert columns to appropriate types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')

            # Ensure data is sorted chronologically
            df = df.sort_index()

            print(f"Successfully loaded {len(df)} data points from '{file_path}'.")
            return df
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading or parsing file '{file_path}': {e}")
        return None
