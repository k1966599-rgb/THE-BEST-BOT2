import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """
    Calculates ATR and a basic volatility signal.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    high_price = df['high']
    low_price = df['low']
    close_price = df['close']

    # Basic ATR calculation
    atr_series = ta.atr(high=high_price, low=low_price, close=close_price, length=length, append=False)

    if atr_series is None:
        return indicators_df

    atr_col = f'ATRr_{length}' # pandas-ta default name for ATR is ATRr (ranged)
    indicators_df[atr_col] = atr_series

    # ATR Volatility Classification
    atr_percentile_20 = indicators_df[atr_col].rolling(100).quantile(0.2)
    atr_percentile_80 = indicators_df[atr_col].rolling(100).quantile(0.8)
    
    vol_col = f'ATR_Volatility_{length}'
    indicators_df[vol_col] = 'Normal'
    indicators_df.loc[indicators_df[atr_col] <= atr_percentile_20, vol_col] = 'Low'
    indicators_df.loc[indicators_df[atr_col] >= atr_percentile_80, vol_col] = 'High'
    
    return indicators_df
