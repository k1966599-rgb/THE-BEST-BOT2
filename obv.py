import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates OBV and provides a trend confirmation signal.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']
    volume = df['volume']

    # Basic OBV calculation
    obv_series = ta.obv(close=close_price, volume=volume, append=False)

    if obv_series is None:
        return indicators_df

    indicators_df['OBV'] = obv_series

    # OBV Trend vs Price Trend Confirmation
    obv_slope = indicators_df['OBV'].rolling(5).mean().diff()
    price_slope = close_price.rolling(5).mean().diff()
    
    indicators_df['OBV_Signal'] = 'Hold'
    
    confirm_up = (obv_slope > 0) & (price_slope > 0)
    confirm_down = (obv_slope < 0) & (price_slope < 0)

    indicators_df.loc[confirm_up, 'OBV_Signal'] = 'Confirm_Up'
    indicators_df.loc[confirm_down, 'OBV_Signal'] = 'Confirm_Down'

    # Basic Divergence
    bullish_div = (obv_slope > 0) & (price_slope < 0)
    bearish_div = (obv_slope < 0) & (price_slope > 0)

    indicators_df.loc[bullish_div, 'OBV_Signal'] = 'Bullish_Divergence'
    indicators_df.loc[bearish_div, 'OBV_Signal'] = 'Bearish_Divergence'

    return indicators_df
