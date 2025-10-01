import pytest
import pandas as pd
from src.strategies.fibo_analyzer import FiboAnalyzer

# A mock fetcher class since FiboAnalyzer requires it for initialization.
class MockFetcher:
    def __init__(self, config):
        pass

@pytest.fixture
def mock_config():
    """Provides a mock configuration with all necessary parameters."""
    return {
        'strategy_params': {
            'fibo_strategy': {
                'sma_period_fast': 5, 'sma_period_slow': 10, 'rsi_period': 14,
                'adx_window': 14, 'atr_window': 14, 'stoch_window': 14, 'volume_period': 20,
                'swing_lookback_period': 50, 'swing_comparison_window': 3,
                'adx_trend_threshold': 20, 'signal_threshold': 3,
                'require_adx_confirmation': False,
                'trend_confirmation_multiplier': 1.5,
                'mta_confidence_modifier': 15,
                'volume_spike_multiplier': 2.0,
                'scoring_weights': {
                    'rsi_confirm': 1, 'macd_confirm': 1, 'reversal_pattern': 2,
                    'volume_spike': 2, 'obv_confirm': 2
                }
            }
        },
        'risk_management': {'atr_multiplier_sl': 2.0}
    }

@pytest.fixture
def sample_uptrend_data():
    """
    Creates a sample DataFrame with a guaranteed rising OBV at the end.
    This version has a flat period followed by a sharp breakout.
    """
    base_price, data_len = 100, 100
    timestamps = pd.to_datetime(pd.date_range(start='2023-01-01', periods=data_len, freq='H'))

    close = [base_price] * data_len
    volume = [1000] * data_len
    # Periods 0-94: Sideways/choppy market to keep OBV relatively flat
    for i in range(1, 95):
        close[i] = base_price + (0.1 if i % 2 == 0 else -0.1)

    # Periods 95-99: Strong breakout with high volume to create a sharp OBV spike
    for i in range(95, 100):
        close[i] = close[i-1] + 5.0 # Very sharp price increase
        volume[i] = 10000          # Very high volume

    high = [p + 1.0 for p in close]
    low = [p - 1.0 for p in close]
    open_prices = list(close)

    # Ensure last 5 candles are bullish for OBV calculation
    for i in range(95, 100):
        open_prices[i] = close[i] - 1.0

    # Manually set swing points to ensure fibo_trend is 'up'
    low[70] = base_price - 10 # Swing Low
    high[90] = base_price + 5 # Swing High

    df = pd.DataFrame({'timestamp': timestamps, 'open': open_prices, 'high': high, 'low': low, 'close': close, 'volume': volume})
    df['timestamp'] = df['timestamp'].astype('int64') // 10**6
    return df

def test_obv_confirmation_increases_score(mock_config, sample_uptrend_data):
    """
    Tests that a confirming OBV trend correctly increases the analysis score.
    """
    mock_fetcher = MockFetcher(mock_config)

    config_with_obv = mock_config
    config_no_obv = mock_config.copy()
    config_no_obv['strategy_params']['fibo_strategy']['scoring_weights']['obv_confirm'] = 0

    analyzer_with_obv = FiboAnalyzer(config=config_with_obv, fetcher=mock_fetcher)
    analyzer_no_obv = FiboAnalyzer(config=config_no_obv, fetcher=mock_fetcher)

    # Act - Use .copy() to prevent DataFrame mutation between calls
    result_with_obv = analyzer_with_obv.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H')
    result_no_obv = analyzer_no_obv.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H')

    # Assert
    assert result_with_obv.get('signal') == 'BUY', "A BUY signal should be generated"
    assert result_with_obv.get('score', 0) > result_no_obv.get('score', 0), \
        f"Score with OBV ({result_with_obv.get('score', 0)}) should be higher than without ({result_no_obv.get('score', 0)})"

def test_mta_alignment_boosts_confidence(mock_config, sample_uptrend_data):
    """
    Tests that MTA alignment correctly increases the final confidence score.
    """
    mock_fetcher = MockFetcher(mock_config)
    analyzer = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher, timeframe='1H')

    # Use .copy() to prevent DataFrame mutation
    base_result = analyzer.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H', higher_tf_trend_info=None)
    base_confidence = base_result.get('confidence', 0)

    aligned_htf_info = {'trend': 'up', 'timeframe': '4H'}
    aligned_result = analyzer.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H', higher_tf_trend_info=aligned_htf_info)
    aligned_confidence = aligned_result.get('confidence', 0)

    expected_confidence = min(100, base_confidence + mock_config['strategy_params']['fibo_strategy']['mta_confidence_modifier'])
    assert aligned_confidence == expected_confidence

def test_mta_conflict_reduces_confidence(mock_config, sample_uptrend_data):
    """
    Tests that MTA conflict correctly decreases the final confidence score.
    """
    mock_fetcher = MockFetcher(mock_config)
    analyzer = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher, timeframe='1H')

    # Use .copy() to prevent DataFrame mutation
    base_result = analyzer.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H', higher_tf_trend_info=None)
    base_confidence = base_result.get('confidence', 0)

    conflicting_htf_info = {'trend': 'down', 'timeframe': '4H'}
    conflicting_result = analyzer.get_analysis(sample_uptrend_data.copy(), 'TEST-USDT', '1H', higher_tf_trend_info=conflicting_htf_info)
    conflicting_confidence = conflicting_result.get('confidence', 0)

    expected_confidence = max(0, base_confidence - mock_config['strategy_params']['fibo_strategy']['mta_confidence_modifier'])
    assert conflicting_confidence == expected_confidence