import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

def apply_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies a curated set of key technical indicators to the DataFrame using pandas_ta.
    This is a more lightweight approach than calculating all possible indicators.

    Args:
        df: DataFrame with columns 'open', 'high', 'low', 'close', 'volume'.

    Returns:
        DataFrame with added indicator columns.
    """
    if df.empty:
        logger.warning("Input DataFrame is empty. Skipping indicator application.")
        return df

    logger.info(f"Applying a curated set of technical indicators to DataFrame with {len(df)} rows.")

    # Create a copy to avoid SettingWithCopyWarning
    df_with_indicators = df.copy()

    try:
        # Apply a specific, controlled set of indicators
        df_with_indicators.ta.rsi(length=14, append=True)
        df_with_indicators.ta.macd(fast=12, slow=26, signal=9, append=True)
        df_with_indicators.ta.bbands(length=20, std=2, append=True)
        df_with_indicators.ta.atr(length=14, append=True)
        df_with_indicators.ta.obv(append=True)
        df_with_indicators.ta.adx(length=14, append=True)
        df_with_indicators.ta.stoch(k=14, d=3, smooth_k=3, append=True)
        df_with_indicators.ta.sma(length=20, append=True)
        df_with_indicators.ta.sma(length=50, append=True)
        df_with_indicators.ta.ema(length=200, append=True)

        # Clean up column names for better readability
        df_with_indicators.columns = [col.lower() for col in df_with_indicators.columns]

        logger.info(f"Successfully applied indicators. DataFrame now has {len(df_with_indicators.columns)} columns.")

    except Exception as e:
        logger.exception("An error occurred during indicator application with pandas_ta.")
        # In case of an error, return the original DataFrame
        return df

    return df_with_indicators
