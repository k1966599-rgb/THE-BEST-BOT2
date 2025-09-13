import pandas as pd
import logging

logger = logging.getLogger(__name__)

def standardize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardizes the column names of a trading data DataFrame.

    This function performs several operations:
    - Converts all column names to lowercase.
    - Removes leading/trailing whitespace from column names.
    - Maps common variations (e.g., 'datetime', 'time') to a standard name.
    - Validates that all required columns ('open', 'high', 'low', 'close',
      'volume', 'timestamp') are present after standardization.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with standardized column names.

    Raises:
        ValueError: If a required column is missing after standardization.
    """
    if df.empty:
        logger.warning("Input DataFrame is empty. Skipping standardization.")
        return df

    # Make a copy to avoid modifying the original DataFrame outside the function scope
    df_std = df.copy()

    # 1. Convert column names to lowercase and strip whitespace
    df_std.columns = df_std.columns.str.lower().str.strip()

    # 2. Map common variations to standard names
    column_mapping = {
        'time': 'timestamp',
        'datetime': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    # Apply renaming only for columns that exist in the DataFrame
    df_std.rename(columns={k: v for k, v in column_mapping.items() if k in df_std.columns}, inplace=True)

    # 3. Validate that all required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
    missing_cols = [col for col in required_cols if col not in df_std.columns]

    if missing_cols:
        error_msg = f"Missing required columns after standardization: {missing_cols}. Available columns: {df_std.columns.tolist()}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # 4. Convert columns to correct data types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df_std[col] = pd.to_numeric(df_std[col], errors='coerce')

    # Ensure timestamp is an integer type for indexing
    df_std['timestamp'] = df_std['timestamp'].astype(int)

    # Drop rows with NaN values that may have been introduced by coercion
    df_std.dropna(inplace=True)

    logger.info("DataFrame columns successfully standardized and converted to numeric types.")
    return df_std
