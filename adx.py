import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_adx(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """
    Calculates ADX, DI+, DI- and provides a basic trend strength signal.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    high_price = df['high']
    low_price = df['low']
    close_price = df['close']

    # Basic ADX calculation
    adx_df = ta.adx(high=high_price, low=low_price, close=close_price, length=length, append=False)
    
    if adx_df is None or adx_df.empty:
        return indicators_df

    indicators_df = indicators_df.join(adx_df)
    
    adx_col = f'ADX_{length}'
    dmp_col = f'DMP_{length}'
    dmn_col = f'DMN_{length}'

    if not all(col in indicators_df.columns for col in [adx_col, dmp_col, dmn_col]):
        return pd.DataFrame(index=df.index)

    # ADX Trend Strength Classification
    strength_col = f'ADX_Trend_{length}'
    indicators_df[strength_col] = 'No_Trend'
    indicators_df.loc[indicators_df[adx_col] > 20, strength_col] = 'Weak_Trend'
    indicators_df.loc[indicators_df[adx_col] > 25, strength_col] = 'Strong_Trend'

    # Add trend direction based on DI+ and DI-
    direction_col = f'ADX_Direction_{length}'
    indicators_df[direction_col] = np.where(indicators_df[dmp_col] > indicators_df[dmn_col], 'Bullish', 'Bearish')

    return indicators_df
