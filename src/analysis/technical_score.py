import pandas as pd
from typing import Dict, Any
from .base_analysis import BaseAnalysis

class TechnicalIndicators(BaseAnalysis):
    def __init__(self, config: dict = None, timeframe: str = None):
        super().__init__(config, timeframe)
        self.rsi_period = self.config.get('RSI_PERIOD', 14)
        self.macd_fast = self.config.get('MACD_FAST', 12)
        self.macd_slow = self.config.get('MACD_SLOW', 26)
        self.macd_signal = self.config.get('MACD_SIGNAL', 9)
        self.sma_short = self.config.get('SMA_SHORT', 20)
        self.sma_long = self.config.get('SMA_LONG', 50)
        self.rsi_oversold = self.config.get('RSI_OVERSOLD', 30)
        self.rsi_overbought = self.config.get('RSI_OVERBOUGHT', 70)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < self.sma_long:
            return {'error': f'Not enough data. Need {self.sma_long} periods.', 'total_score': 0}

        latest = df.iloc[-1]
        total_score = 0

        # Correct column names from pandas_ta (they are usually lowercase)
        macd_col = f'macd_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
        macds_col = f'macds_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
        rsi_col = f'rsi_{self.rsi_period}'
        sma_short_col = f'sma_{self.sma_short}'
        sma_long_col = f'sma_{self.sma_long}'

        # MACD Analysis
        if macd_col in latest and macds_col in latest:
            if latest[macd_col] > latest[macds_col]:
                total_score += 2
            else:
                total_score -= 2

        # RSI Analysis
        if rsi_col in latest:
            if latest[rsi_col] > self.rsi_overbought:
                total_score -= 1.5
            elif latest[rsi_col] < self.rsi_oversold:
                total_score += 1.5
            else:
                total_score += 0.5

        # SMA Crossover Analysis
        if sma_short_col in latest and sma_long_col in latest:
            if latest[sma_short_col] > latest[sma_long_col]:
                total_score += 2
            else:
                total_score -= 2

        # Price relative to short SMA
        if 'close' in latest and sma_short_col in latest:
            if latest['close'] > latest[sma_short_col]:
                total_score += 1
            else:
                total_score -=1

        return {'total_score': round(total_score, 2)}
