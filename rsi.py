import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """
    Calculates RSI, identifies overbought/oversold levels, and basic divergence.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']
    high_price = df['high']
    low_price = df['low']

    # Basic RSI calculation
    rsi_series = ta.rsi(close=close_price, length=length, append=False)
    
    if rsi_series is None:
        return indicators_df # Return empty df if calculation fails

    rsi_col = f'RSI_{length}'
    indicators_df[rsi_col] = rsi_series

    # --- Signal Generation ---

    # 1. Overbought/Oversold Signal
    indicators_df[f'RSI_Signal_{length}'] = 'Neutral'
    indicators_df.loc[indicators_df[rsi_col] > 70, f'RSI_Signal_{length}'] = 'Overbought'
    indicators_df.loc[indicators_df[rsi_col] < 30, f'RSI_Signal_{length}'] = 'Oversold'

    # 2. Basic Divergence Detection
    indicators_df[f'RSI_Divergence_{length}'] = 'None'

    # Find last two peaks in price and RSI for bearish divergence
    price_peaks = high_price[high_price > high_price.shift(1)]
    price_peaks = price_peaks[price_peaks > price_peaks.shift(-1)]
    
    if len(price_peaks) >= 2:
        last_two_price_peaks = price_peaks.tail(2)
        p_peak_1_idx, p_peak_2_idx = last_two_price_peaks.index
        p_peak_1_val, p_peak_2_val = last_two_price_peaks.values

        rsi_at_p_peak_1 = indicators_df[rsi_col].loc[p_peak_1_idx]
        rsi_at_p_peak_2 = indicators_df[rsi_col].loc[p_peak_2_idx]

        # Check for bearish divergence (Higher High in price, Lower High in RSI)
        if p_peak_2_val > p_peak_1_val and rsi_at_p_peak_2 < rsi_at_p_peak_1:
            indicators_df.loc[p_peak_2_idx, f'RSI_Divergence_{length}'] = 'Bearish'

    # Find last two troughs in price and RSI for bullish divergence
    price_troughs = low_price[low_price < low_price.shift(1)]
    price_troughs = price_troughs[price_troughs < price_troughs.shift(-1)]

    if len(price_troughs) >= 2:
        last_two_price_troughs = price_troughs.tail(2)
        p_trough_1_idx, p_trough_2_idx = last_two_price_troughs.index
        p_trough_1_val, p_trough_2_val = last_two_price_troughs.values

        rsi_at_p_trough_1 = indicators_df[rsi_col].loc[p_trough_1_idx]
        rsi_at_p_trough_2 = indicators_df[rsi_col].loc[p_trough_2_idx]

        # Check for bullish divergence (Lower Low in price, Higher Low in RSI)
        if p_trough_2_val < p_trough_1_val and rsi_at_p_trough_2 > rsi_at_p_trough_1:
            indicators_df.loc[p_trough_2_idx, f'RSI_Divergence_{length}'] = 'Bullish'

    return indicators_df
