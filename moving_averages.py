import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import List

def calculate_sma(df: pd.DataFrame, lengths: List[int]) -> pd.DataFrame:
    """
    Enhanced SMA calculation with trend analysis and crossover detection.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']

    for length in lengths:
        sma_series = ta.sma(close=close_price, length=length, append=False)

        if sma_series is not None:
            sma_col = f'SMA_{length}'
            indicators_df[sma_col] = sma_series
            
            # Price vs SMA position
            indicators_df[f'SMA_Position_{length}'] = np.where(close_price > indicators_df[sma_col], 'Above', 'Below')
            
            # SMA slope/trend
            sma_slope = indicators_df[sma_col].rolling(5).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0.0)
            indicators_df[f'SMA_Trend_{length}'] = np.where(sma_slope > 0, 'Rising', 'Falling')
            
            # Distance from SMA (percentage)
            indicators_df[f'SMA_Distance_{length}'] = ((close_price - indicators_df[sma_col]) / indicators_df[sma_col] * 100).round(2)
            
            # SMA crossover signals
            cross_up = (close_price > indicators_df[sma_col]) & (close_price.shift(1) <= indicators_df[sma_col].shift(1))
            cross_down = (close_price < indicators_df[sma_col]) & (close_price.shift(1) >= indicators_df[sma_col].shift(1))
            
            indicators_df[f'SMA_Cross_{length}'] = 'None'
            indicators_df.loc[cross_up, f'SMA_Cross_{length}'] = 'Bullish'
            indicators_df.loc[cross_down, f'SMA_Cross_{length}'] = 'Bearish'
            
            # SMA strength (how long price has been on one side)
            position_changed = indicators_df[f'SMA_Position_{length}'].ne(indicators_df[f'SMA_Position_{length}'].shift())
            indicators_df[f'SMA_Strength_{length}'] = position_changed.groupby(position_changed.cumsum()).cumcount() + 1
    
    # Multi-timeframe SMA analysis if multiple lengths provided
    if len(lengths) >= 2:
        short_sma_col = f'SMA_{min(lengths)}'
        long_sma_col = f'SMA_{max(lengths)}'
        
        if short_sma_col in indicators_df.columns and long_sma_col in indicators_df.columns:
            short_sma = indicators_df[short_sma_col]
            long_sma = indicators_df[long_sma_col]

            # Golden/Death Cross
            golden_cross = (short_sma > long_sma) & (short_sma.shift(1) <= long_sma.shift(1))
            death_cross = (short_sma < long_sma) & (short_sma.shift(1) >= long_sma.shift(1))
            
            indicators_df[f'Golden_Cross_{min(lengths)}_{max(lengths)}'] = golden_cross
            indicators_df[f'Death_Cross_{min(lengths)}_{max(lengths)}'] = death_cross
            
    return indicators_df

def calculate_ema(df: pd.DataFrame, lengths: List[int]) -> pd.DataFrame:
    """
    Enhanced EMA calculation with responsiveness analysis and trend detection.
    Returns a DataFrame with ONLY the new indicator columns.
    """
    indicators_df = pd.DataFrame(index=df.index)
    close_price = df['close']

    for length in lengths:
        ema_series = ta.ema(close=close_price, length=length, append=False)

        if ema_series is not None:
            ema_col = f'EMA_{length}'
            indicators_df[ema_col] = ema_series
            
            # Price vs EMA position
            indicators_df[f'EMA_Position_{length}'] = np.where(close_price > indicators_df[ema_col], 'Above', 'Below')
            
            # EMA slope/trend (more responsive than SMA)
            ema_slope = indicators_df[ema_col].rolling(3).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0.0)
            indicators_df[f'EMA_Trend_{length}'] = np.where(ema_slope > 0, 'Rising', 'Falling')
            
            # EMA momentum (rate of change)
            indicators_df[f'EMA_Momentum_{length}'] = indicators_df[ema_col].pct_change(periods=2) * 100
            
            # Distance from EMA (percentage)
            indicators_df[f'EMA_Distance_{length}'] = ((close_price - indicators_df[ema_col]) / indicators_df[ema_col] * 100).round(2)
            
            # EMA crossover signals
            cross_up = (close_price > indicators_df[ema_col]) & (close_price.shift(1) <= indicators_df[ema_col].shift(1))
            cross_down = (close_price < indicators_df[ema_col]) & (close_price.shift(1) >= indicators_df[ema_col].shift(1))
            
            indicators_df[f'EMA_Cross_{length}'] = 'None'
            indicators_df.loc[cross_up, f'EMA_Cross_{length}'] = 'Bullish'
            indicators_df.loc[cross_down, f'EMA_Cross_{length}'] = 'Bearish'
    
    # Multi-EMA analysis
    if len(lengths) >= 2:
        fast_ema_col = f'EMA_{min(lengths)}'
        slow_ema_col = f'EMA_{max(lengths)}'
        
        if fast_ema_col in indicators_df.columns and slow_ema_col in indicators_df.columns:
            fast_ema = indicators_df[fast_ema_col]
            slow_ema = indicators_df[slow_ema_col]
            # EMA crossover system
            ema_cross_up = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
            ema_cross_down = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))
            
            indicators_df['EMA_Multi_Signal'] = 'Hold'
            indicators_df.loc[ema_cross_up, 'EMA_Multi_Signal'] = 'Fast_Cross_Up'
            indicators_df.loc[ema_cross_down, 'EMA_Multi_Signal'] = 'Fast_Cross_Down'

    return indicators_df
