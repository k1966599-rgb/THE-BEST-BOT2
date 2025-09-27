import pytest
import pandas as pd
import numpy as np
from src.strategies.fibo_analyzer import FiboAnalyzer
from src.strategies.exceptions import InsufficientDataError
from src.config import get_config

# We can use the fixtures from conftest.py directly as arguments.

def create_uptrend_data(periods=300):
    """
    Helper function to create a DataFrame representing a steady uptrend.
    """
    base_prices = np.linspace(100, 200, periods)
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=periods, freq='H')),
        'open': base_prices - 2,
        'high': base_prices + 3,
        'low': base_prices - 3,
        'close': base_prices,
        'volume': np.linspace(1000, 2000, periods)
    }
    df = pd.DataFrame(data)
    df['timestamp'] = df['timestamp'].apply(lambda x: int(x.timestamp() * 1000))
    return df

def test_buy_signal_on_strong_uptrend(mock_config, mock_fetcher):
    """
    GIVEN a clear uptrend with multiple bullish confirmations.
    WHEN the analyzer processes the data.
    THEN it should return a 'BUY' signal.
    """
    # 1. Arrange
    # Create data that should strongly signal a buy
    buy_data = create_uptrend_data(300)

    # Manually create a final bullish candle with a volume spike
    last_row = buy_data.iloc[-1].copy()
    last_row['open'] = 198
    last_row['close'] = 205 # Bullish candle
    last_row['volume'] = 5000 # Spike
    buy_data.iloc[-1] = last_row

    # Initialize the analyzer for a non-1D timeframe to use default params
    analyzer = FiboAnalyzer(mock_config, mock_fetcher, timeframe="4H")

    # 2. Act
    result = analyzer.get_analysis(buy_data, "BTC-USDT", "4H")

    # 3. Assert
    # With a strong uptrend, high RSI, bullish candle, and volume spike,
    # the score should be high enough to trigger a BUY signal.
    assert result['signal'] == 'BUY', f"Expected BUY signal, but got {result['signal']}. Reason: {result.get('final_reason')}"
    assert result['score'] >= mock_config['strategy_params']['fibo_strategy']['signal_threshold']
    assert "مؤشر القوة النسبية فوق 50" in " ".join(result['reasons'])
    assert "تأكيد طفرة حجم تداول صاعدة" in " ".join(result['reasons'])

def create_downtrend_data(periods=300):
    """
    Helper function to create a DataFrame representing a steady downtrend.
    """
    base_prices = np.linspace(200, 100, periods)
    data = {
        'timestamp': pd.to_datetime(pd.date_range(start='2023-01-01', periods=periods, freq='H')),
        'open': base_prices + 2,
        'high': base_prices + 3,
        'low': base_prices - 3,
        'close': base_prices,
        'volume': np.linspace(1000, 2000, periods)
    }
    df = pd.DataFrame(data)
    df['timestamp'] = df['timestamp'].apply(lambda x: int(x.timestamp() * 1000))
    return df

def test_sell_signal_on_strong_downtrend(mock_config, mock_fetcher):
    """
    GIVEN a clear downtrend with multiple bearish confirmations.
    WHEN the analyzer processes the data.
    THEN it should return a 'SELL' signal.
    """
    # 1. Arrange
    sell_data = create_downtrend_data(300)

    # Manually create a final bearish candle with a volume spike
    last_row = sell_data.iloc[-1].copy()
    last_row['open'] = 105
    last_row['close'] = 98 # Bearish candle
    last_row['volume'] = 5000 # Spike
    sell_data.iloc[-1] = last_row

    analyzer = FiboAnalyzer(mock_config, mock_fetcher, timeframe="1H")

    # 2. Act
    result = analyzer.get_analysis(sell_data, "BTC-USDT", "1H")

    # 3. Assert
    assert result['signal'] == 'SELL', f"Expected SELL signal, but got {result['signal']}. Reason: {result.get('final_reason')}"
    assert result['score'] >= mock_config['strategy_params']['fibo_strategy']['signal_threshold']
    assert "مؤشر القوة النسبية تحت 50" in " ".join(result['reasons'])
    assert "تأكيد طفرة حجم تداول هابطة" in " ".join(result['reasons'])

def test_insufficient_data_error(mock_config, mock_fetcher):
    """
    GIVEN a DataFrame with very few data points.
    WHEN the analyzer processes the data.
    THEN it should raise an InsufficientDataError.
    """
    # 1. Arrange
    # Create data with only 20 candles, which is less than any lookback period.
    insufficient_data = create_uptrend_data(20)
    analyzer = FiboAnalyzer(mock_config, mock_fetcher, timeframe="1H")

    # 2. Act & 3. Assert
    # We expect the get_analysis function to raise this specific error.
    # pytest.raises will catch the error and pass the test if it's raised.
    # If no error (or a different error) is raised, the test will fail.
    with pytest.raises(InsufficientDataError) as excinfo:
        analyzer.get_analysis(insufficient_data, "BTC-USDT", "1H")

    # Optional: Check the error message content
    assert "Not enough data for swing analysis" in str(excinfo.value)