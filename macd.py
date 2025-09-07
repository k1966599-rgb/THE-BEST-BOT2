import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates MACD, its signal line, histogram, and detects crossovers and basic divergences.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']
    high_price = df['high']
    low_price = df['low']

    # Basic MACD calculation using the ta library function
    macd_df = ta.macd(close=close_price, fast=fast, slow=slow, signal=signal, append=False)
    
    if macd_df is None or macd_df.empty:
        return indicators_df # Return empty df if calculation fails

    # Add base MACD columns to our new dataframe
    indicators_df = indicators_df.join(macd_df)

    macd_col = f'MACD_{fast}_{slow}_{signal}'
    signal_col = f'MACDs_{fast}_{slow}_{signal}'
    hist_col = f'MACDh_{fast}_{slow}_{signal}'

    # Ensure all required columns were calculated
    if not all(col in indicators_df.columns for col in [macd_col, signal_col, hist_col]):
        return pd.DataFrame(index=df.index) # return empty if base cols are missing

    # --- Signal Generation ---
    macd_series = indicators_df[macd_col]
    signal_series = indicators_df[signal_col]

    # 1. Crossover Detection
    bullish_cross = (macd_series.shift(1) < signal_series.shift(1)) & (macd_series > signal_series)
    bearish_cross = (macd_series.shift(1) > signal_series.shift(1)) & (macd_series < signal_series)

    indicators_df[f'MACD_Crossover_{fast}_{slow}_{signal}'] = 'None'
    indicators_df.loc[bullish_cross, f'MACD_Crossover_{fast}_{slow}_{signal}'] = 'Bullish_Cross'
    indicators_df.loc[bearish_cross, f'MACD_Crossover_{fast}_{slow}_{signal}'] = 'Bearish_Cross'

    # 2. Main Signal (Buy/Sell/Hold)
    indicators_df[f'MACD_Signal_{fast}_{slow}_{signal}'] = 'Hold'
    indicators_df.loc[bullish_cross, f'MACD_Signal_{fast}_{slow}_{signal}'] = 'Buy'
    indicators_df.loc[bearish_cross, f'MACD_Signal_{fast}_{slow}_{signal}'] = 'Sell'

    # Add "Strong" modifier based on histogram and position
    strong_buy_cond = bullish_cross & (indicators_df[hist_col] > 0)
    strong_sell_cond = bearish_cross & (indicators_df[hist_col] < 0)
    indicators_df.loc[strong_buy_cond, f'MACD_Signal_{fast}_{slow}_{signal}'] = 'Strong_Buy'
    indicators_df.loc[strong_sell_cond, f'MACD_Signal_{fast}_{slow}_{signal}'] = 'Strong_Sell'

    # 3. Divergence Detection
    indicators_df[f'MACD_Divergence_{fast}_{slow}_{signal}'] = 'None'

    price_peaks = high_price[high_price > high_price.shift(1)]
    price_peaks = price_peaks[price_peaks > price_peaks.shift(-1)]

    if len(price_peaks) >= 2:
        last_two_price_peaks = price_peaks.tail(2)
        p_peak_1_idx, p_peak_2_idx = last_two_price_peaks.index
        p_peak_1_val, p_peak_2_val = last_two_price_peaks.values

        macd_at_p_peak_1 = macd_series.loc[p_peak_1_idx]
        macd_at_p_peak_2 = macd_series.loc[p_peak_2_idx]

        if (p_peak_2_val > p_peak_1_val) and (macd_at_p_peak_2 < macd_at_p_peak_1):
            indicators_df.loc[p_peak_2_idx, f'MACD_Divergence_{fast}_{slow}_{signal}'] = 'Bearish_Div'

    price_troughs = low_price[low_price < low_price.shift(1)]
    price_troughs = price_troughs[price_troughs < price_troughs.shift(-1)]

    if len(price_troughs) >= 2:
        last_two_price_troughs = price_troughs.tail(2)
        p_trough_1_idx, p_trough_2_idx = last_two_price_troughs.index
        p_trough_1_val, p_trough_2_val = last_two_price_troughs.values
        
        macd_at_p_trough_1 = macd_series.loc[p_trough_1_idx]
        macd_at_p_trough_2 = macd_series.loc[p_trough_2_idx]

        if (p_trough_2_val < p_trough_1_val) and (macd_at_p_trough_2 > macd_at_p_trough_1):
            indicators_df.loc[p_trough_2_idx, f'MACD_Divergence_{fast}_{slow}_{signal}'] = 'Bullish_Div'
            
    # Add a position column for downstream logic if needed
    indicators_df[f'MACD_Position_{fast}_{slow}'] = np.where(macd_series > 0, 'Bullish', 'Bearish')

    return indicators_df
