import pandas as pd
import logging

logger = logging.getLogger(__name__)

def standardize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes the column names of a trading data DataFrame.
    - Converts all column names to lowercase.
    - Removes leading/trailing whitespace.
    - Maps common variations (e.g., 'datetime', 'time') to a standard name ('timestamp').
    - Validates that all required columns are present.

    :param df: The input DataFrame.
    :return: The standardized DataFrame.
    :raises ValueError: If a required column is missing after standardization.
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
        'date': 'timestamp',
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

    logger.info("DataFrame columns successfully standardized.")
    return df_std
