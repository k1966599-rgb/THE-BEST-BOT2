import pytest
import pandas as pd
from src.strategies.fibo_analyzer import FiboAnalyzer

# A mock fetcher class since FiboAnalyzer requires it for initialization,
# but it's not used within the get_analysis method itself.
class MockFetcher:
    def __init__(self, config):
        pass

@pytest.fixture
def mock_config():
    """Provides a mock configuration for the FiboAnalyzer test."""
    return {
        'strategy_params': {
            'fibo_strategy': {
                'sma_period_fast': 5,
                'sma_period_slow': 10,
                'rsi_period': 14,
                'adx_window': 14,
                'atr_window': 14,
                'stoch_window': 14,
                'swing_lookback_period': 50,
                'swing_comparison_window': 3,
                'adx_trend_threshold': 20,
                'signal_threshold': 3,  # Lower threshold for easier testing
                'require_adx_confirmation': False,  # Disable for simpler testing
                'scoring_weights': {
                    'confluence_zone': 2,
                    'rsi_confirm': 1,
                    'macd_confirm': 1,
                    'stoch_confirm': 1,
                    'reversal_pattern': 2,
                    'volume_spike': 2
                }
            }
        },
        'risk_management': {
            'atr_multiplier_sl': 2.0
        }
    }

@pytest.fixture
def sample_uptrend_data():
    """
    Creates a sample DataFrame with a clear uptrend and swing points
    designed to trigger a BUY signal.
    """
    base_price = 100
    data_len = 100
    timestamps = pd.to_datetime(pd.date_range(start='2023-01-01', periods=data_len, freq='H'))

    # Create a steady uptrend
    close = [base_price + i * 0.5 for i in range(data_len)]
    high = [p + 2.0 for p in close]
    low = [p - 2.0 for p in close]
    open_prices = list(close)
    volume = [1000 + i * 10 for i in range(data_len)]

    # Craft a clear swing low within the lookback period (last 50 candles)
    # at index 70 (which is index 20 in the 50-candle lookback window)
    low[70] = base_price + 70 * 0.5 - 15

    # Craft a clear swing high after the low
    # at index 90 (index 40 in the lookback window)
    high[90] = base_price + 90 * 0.5 + 15

    # Add a volume spike on the last candle to increase the confirmation score
    volume[-1] = 5000
    # Make the last candle bullish to ensure the volume spike is counted
    open_prices[-1] = close[-1] - 1

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
    # The analyzer expects timestamp in milliseconds
    df['timestamp'] = df['timestamp'].astype('int64') // 10**6
    return df

def test_fibo_analyzer_identifies_buy_signal_in_uptrend(mock_config, sample_uptrend_data):
    """
    Tests that FiboAnalyzer correctly identifies a BUY signal in a clear uptrend scenario.
    """
    # Arrange
    mock_fetcher = MockFetcher(mock_config)
    analyzer = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher, timeframe='1H')

    # Act
    analysis_result = analyzer.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H')

    # Assert
    assert analysis_result is not None, "Analysis result should not be None"

    # Check for identified swings
    assert 'swing_high' in analysis_result and analysis_result['swing_high'], "Should identify a swing high"
    assert 'swing_low' in analysis_result and analysis_result['swing_low'], "Should identify a swing low"

    # With the crafted data (uptrend, swing low then high), the fibo_trend should be 'up'
    assert analysis_result.get('fibo_trend') == 'up', "Fibonacci trend should be 'up'"

    # With crafted data and low threshold, it should generate a BUY signal.
    # The score should be high enough because RSI > 50, MACD is positive, etc.
    assert analysis_result.get('signal') == 'BUY', \
        f"Signal should be BUY, but got {analysis_result.get('signal')}. Reason: {analysis_result.get('final_reason')}"

    # Check for a positive score
    assert analysis_result.get('score', 0) > 0, "Score should be positive for a BUY signal"

    # Check if scenarios were generated
    assert 'scenarios' in analysis_result and analysis_result['scenarios'], "Scenarios should be generated"
    assert 'scenario1' in analysis_result['scenarios'], "Scenario 1 should exist"
    assert analysis_result['scenarios']['scenario1']['title'] == "صعود نحو الأهداف"