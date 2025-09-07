import pytest
import sys
import os
import pandas as pd
import json
import numpy as np

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.fibonacci import FibonacciAnalysis
from indicators import apply_all_indicators

@pytest.fixture(scope="module")
def historical_data_df():
    """Loads sample historical data from a JSON file and returns a DataFrame."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'test_okx_data', 'BTC-USDT_historical.json')
    with open(file_path, 'r') as f:
        json_data = json.load(f)

    df = pd.DataFrame(json_data['data'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.drop(columns=['date'], inplace=True)
    df = df.astype(float)
    return df

@pytest.fixture(scope="module")
def df_with_indicators(historical_data_df):
    """
    Prepares the DataFrame with indicators using the new refactored `apply_all_indicators` function.
    """
    df = historical_data_df.copy()
    # 1. Rename columns for compatibility
    df.rename(columns={"high": "High", "low": "Low", "open": "Open", "close": "Close", "volume": "Volume"}, inplace=True)

    # 2. Run the refactored indicator application function
    df = apply_all_indicators(df)

    return df

def test_fibonacci_analysis_runs_successfully(df_with_indicators):
    """
    Tests that the FibonacciAnalysis class can be instantiated and run its
    comprehensive analysis without raising errors, returning a valid structure.
    """
    assert not df_with_indicators.empty, "Test fixture failed to provide a DataFrame with indicators."

    fib_analysis = FibonacciAnalysis(df_with_indicators)
    results = fib_analysis.get_comprehensive_fibonacci_analysis()

    assert results is not None
    assert isinstance(results, dict)
    assert 'error' not in results, f"Fibonacci analysis returned an error: {results.get('error')}"

    expected_keys = ['retracement_levels', 'extension_levels', 'fib_score']
    for key in expected_keys:
        assert key in results, f"Result dictionary is missing the key: '{key}'"

    assert isinstance(results['retracement_levels'], list)
    assert isinstance(results['extension_levels'], list)
    assert isinstance(results['fib_score'], (int, float))

    if results['retracement_levels']:
        level_sample = results['retracement_levels'][0]
        assert 'level' in level_sample
        assert 'price' in level_sample
        assert isinstance(level_sample['price'], (float, np.floating))

    if results['extension_levels']:
        level_sample = results['extension_levels'][0]
        assert 'level' in level_sample
        assert 'price' in level_sample
        assert isinstance(level_sample['price'], (float, np.floating))

    print("\nFibonacci analysis test passed successfully.")
    print(f"Fib Score: {results['fib_score']}")
    print(f"Retracement Levels Found: {len(results['retracement_levels'])}")
    print(f"Extension Levels Found: {len(results['extension_levels'])}")
