import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_stoch(df: pd.DataFrame, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    """
    Calculates Stochastic Oscillator and identifies overbought/oversold signals and crossovers.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    high_price = df['high']
    low_price = df['low']
    close_price = df['close']

    # Basic Stochastic calculation
    stoch_df = ta.stoch(high=high_price, low=low_price, close=close_price, k=k, d=d, smooth_k=smooth_k, append=False)

    if stoch_df is None or stoch_df.empty:
        return indicators_df

    indicators_df = indicators_df.join(stoch_df)

    stoch_k_col = f'STOCHk_{k}_{d}_{smooth_k}'
    stoch_d_col = f'STOCHd_{k}_{d}_{smooth_k}'

    if not all(col in indicators_df.columns for col in [stoch_k_col, stoch_d_col]):
        return pd.DataFrame(index=df.index)

    # --- Signal Generation ---
    stoch_k_series = indicators_df[stoch_k_col]
    stoch_d_series = indicators_df[stoch_d_col]

    # 1. Main Signal for technical_score
    signal_col = f'STOCH_Signal_{k}_{d}_{smooth_k}'
    indicators_df[signal_col] = 'Hold'
    indicators_df.loc[stoch_k_series > 80, signal_col] = 'Overbought'
    indicators_df.loc[stoch_k_series < 20, signal_col] = 'Oversold'

    # 2. Crossover Signal
    cross_col = f'STOCH_Cross_{k}_{d}_{smooth_k}'
    bullish_cross = (stoch_k_series.shift(1) < stoch_d_series.shift(1)) & (stoch_k_series > stoch_d_series)
    bearish_cross = (stoch_k_series.shift(1) > stoch_d_series.shift(1)) & (stoch_k_series < stoch_d_series)
    
    indicators_df[cross_col] = 'None'
    indicators_df.loc[bullish_cross, cross_col] = 'Bullish_Cross'
    indicators_df.loc[bearish_cross, cross_col] = 'Bearish_Cross'
    
    return indicators_df
