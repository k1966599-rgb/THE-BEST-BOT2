import pandas as pd
from typing import List, Dict, Any

class DataValidator:
    """
    A class to handle validation of market data.
    """
    @staticmethod
    def validate_and_clean_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Converts a list of candle data into a cleaned and validated DataFrame.

        - Converts key columns to numeric types.
        - Drops rows with missing critical data.
        - Drops duplicate timestamps.
        - Sorts data by timestamp.

        Args:
            data: A list of dictionary objects, where each dict represents a candle.

        Returns:
            A cleaned and validated pandas DataFrame.

        Raises:
            ValueError: If the input data is empty or not in the expected format.
        """
        if not data:
            raise ValueError("Input data for DataFrame creation cannot be empty.")

        df = pd.DataFrame(data)

        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Input data is missing one of the required columns: {required_cols}")

        # Convert all relevant columns to numeric types
        numeric_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Drop rows with NaN in critical columns
        df.dropna(subset=required_cols, inplace=True)

        # Drop duplicates and sort
        df = df.drop_duplicates(subset=['timestamp']).sort_values(by='timestamp', ascending=True).reset_index(drop=True)

        return df