import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_bbands(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Bollinger Bands and identifies signals based on price interaction with the bands.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']

    # Basic Bollinger Bands calculation
    bbands_df = ta.bbands(close=close_price, length=length, std=std, append=False)
    
    if bbands_df is None or bbands_df.empty:
        return indicators_df

    indicators_df = indicators_df.join(bbands_df)
    
    # Standard column names might vary slightly based on pandas_ta version, so find them
    upper_col = next((col for col in bbands_df.columns if 'BBU' in col), None)
    middle_col = next((col for col in bbands_df.columns if 'BBM' in col), None)
    lower_col = next((col for col in bbands_df.columns if 'BBL' in col), None)

    if not all([upper_col, middle_col, lower_col]):
        return pd.DataFrame(index=df.index)

    # --- Signal Generation ---

    # 1. Band Position (%B)
    position = ((close_price - indicators_df[lower_col]) / (indicators_df[upper_col] - indicators_df[lower_col]))
    indicators_df[f'BB_Position_{length}_{std}'] = position * 100

    # 2. Main Signal for technical_score
    # Using a clear, simple name for the signal column.
    indicators_df[f'BB_Signal_{length}_{std}'] = 'Hold'
    indicators_df.loc[close_price < indicators_df[lower_col], f'BB_Signal_{length}_{std}'] = 'Touch_Lower'
    indicators_df.loc[close_price > indicators_df[upper_col], f'BB_Signal_{length}_{std}'] = 'Touch_Upper'

    # 3. Squeeze Detection
    bb_width = ((indicators_df[upper_col] - indicators_df[lower_col]) / indicators_df[middle_col])
    # Squeeze is when width is at a low for the last N periods (e.g., 120)
    is_squeeze = bb_width < bb_width.rolling(120).min() * 1.1
    indicators_df[f'BB_Squeeze_{length}_{std}'] = is_squeeze

    return indicators_df
