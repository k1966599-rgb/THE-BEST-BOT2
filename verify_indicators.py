import pandas as pd
import numpy as np
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from indicators import apply_all_indicators

def create_sample_df():
    """Creates a sample DataFrame for verification."""
    np.random.seed(42)
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
    data = {
        'open': np.random.uniform(90, 110, 100).cumsum() + 1000,
        'high': np.random.uniform(0, 5, 100).cumsum() + 1005,
        'low': np.random.uniform(-5, 0, 100).cumsum() + 995,
        'close': np.random.uniform(-2, 2, 100).cumsum() + 1000,
        'volume': np.random.uniform(1000, 5000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df

def main():
    """Main verification function."""
    print("--- Starting Indicator Verification ---")

    # 1. Create sample data
    df = create_sample_df()
    print(f"Original DataFrame created with {len(df.columns)} columns.")
    print("Original columns:", df.columns.tolist())

    # 2. Apply indicators
    df_with_indicators = apply_all_indicators(df)

    # 3. Verify results
    print("\n--- Verification Results ---")
    if len(df_with_indicators.columns) > len(df.columns):
        print(f"✅ SUCCESS: Indicators were added. New column count: {len(df_with_indicators.columns)}")
        added_cols = [col for col in df_with_indicators.columns if col not in df.columns]
        print("A few of the new columns added:", added_cols[:5])

        # Check for a specific key indicator
        if 'rsi_14' in df_with_indicators.columns:
            print("✅ SUCCESS: 'rsi_14' column exists.")
        else:
            print("❌ FAILURE: 'rsi_14' column is missing.")

    else:
        print("❌ FAILURE: No new columns were added to the DataFrame.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
