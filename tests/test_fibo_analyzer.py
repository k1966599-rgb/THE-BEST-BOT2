import pytest
import pandas as pd
from src.strategies.fibo_analyzer import FiboAnalyzer

# A mock fetcher class since FiboAnalyzer requires it for initialization.
class MockFetcher:
    def __init__(self, config):
        pass

@pytest.fixture
def mock_config():
    """Provides a mock configuration with added MTA and weighting parameters."""
    return {
        'strategy_params': {
            'fibo_strategy': {
                'sma_period_fast': 5, 'sma_period_slow': 10, 'rsi_period': 14,
                'adx_window': 14, 'atr_window': 14, 'stoch_window': 14,
                'swing_lookback_period': 50, 'swing_comparison_window': 3,
                'adx_trend_threshold': 20, 'signal_threshold': 3,
                'require_adx_confirmation': False,
                'trend_confirmation_multiplier': 1.5, # Weighted scoring multiplier
                'mta_confidence_modifier': 15,       # MTA confidence modifier
                'scoring_weights': {
                    'rsi_confirm': 1, 'macd_confirm': 1, 'reversal_pattern': 2, 'volume_spike': 2
                }
            }
        },
        'risk_management': {'atr_multiplier_sl': 2.0}
    }

@pytest.fixture
def sample_uptrend_data():
    """Creates a sample DataFrame designed to trigger a BUY signal in an uptrend."""
    base_price, data_len = 100, 100
    timestamps = pd.to_datetime(pd.date_range(start='2023-01-01', periods=data_len, freq='H'))
    close = [base_price + i * 0.5 for i in range(data_len)]
    high = [p + 2.0 for p in close]; low = [p - 2.0 for p in close]
    open_prices = list(close); volume = [1000 + i * 10 for i in range(data_len)]
    low[70] = base_price + 70 * 0.5 - 15  # Swing Low
    high[90] = base_price + 90 * 0.5 + 15 # Swing High
    volume[-1] = 5000; open_prices[-1] = close[-1] - 1 # Volume spike
    df = pd.DataFrame({'timestamp': timestamps, 'open': open_prices, 'high': high, 'low': low, 'close': close, 'volume': volume})
    df['timestamp'] = df['timestamp'].astype('int64') // 10**6
    return df

def test_weighted_scoring_increases_score_on_trend_alignment(mock_config, sample_uptrend_data):
    """
    Tests that the weighted scoring correctly increases the score when the
    fibo_trend aligns with the main_trend.
    """
    mock_fetcher = MockFetcher(mock_config)
    analyzer_no_multiplier = FiboAnalyzer(config={**mock_config, 'strategy_params': {**mock_config['strategy_params'], 'fibo_strategy': {**mock_config['strategy_params']['fibo_strategy'], 'trend_confirmation_multiplier': 1.0}}}, fetcher=mock_fetcher)
    analyzer_with_multiplier = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher)

    # Act
    result_no_multiplier = analyzer_no_multiplier.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H')
    result_with_multiplier = analyzer_with_multiplier.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H')

    # Assert
    # The data is an uptrend, and the fibo signal is 'up', so they align.
    assert result_with_multiplier.get('score', 0) > result_no_multiplier.get('score', 0), \
        "Score should be higher when trend confirmation multiplier is active."

def test_mta_alignment_boosts_confidence(mock_config, sample_uptrend_data):
    """
    Tests that MTA alignment correctly increases the final confidence score.
    """
    mock_fetcher = MockFetcher(mock_config)
    analyzer = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher, timeframe='1H')

    # Act
    # First, get the result without MTA to establish a baseline confidence
    base_result = analyzer.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H', higher_tf_trend_info=None)
    base_confidence = base_result.get('confidence', 0)

    # Now, get the result with an aligning higher timeframe trend
    aligned_htf_info = {'trend': 'up', 'timeframe': '4H'}
    aligned_result = analyzer.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H', higher_tf_trend_info=aligned_htf_info)
    aligned_confidence = aligned_result.get('confidence', 0)

    # Assert
    expected_confidence = min(100, base_confidence + mock_config['strategy_params']['fibo_strategy']['mta_confidence_modifier'])
    assert aligned_confidence == expected_confidence, \
        f"Confidence with MTA alignment should be {expected_confidence}, but got {aligned_confidence}"

def test_mta_conflict_reduces_confidence(mock_config, sample_uptrend_data):
    """
    Tests that MTA conflict correctly decreases the final confidence score.
    """
    mock_fetcher = MockFetcher(mock_config)
    analyzer = FiboAnalyzer(config=mock_config, fetcher=mock_fetcher, timeframe='1H')

    # Act
    base_result = analyzer.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H', higher_tf_trend_info=None)
    base_confidence = base_result.get('confidence', 0)

    # Now, get the result with a conflicting higher timeframe trend
    conflicting_htf_info = {'trend': 'down', 'timeframe': '4H'}
    conflicting_result = analyzer.get_analysis(sample_uptrend_data, 'TEST-USDT', '1H', higher_tf_trend_info=conflicting_htf_info)
    conflicting_confidence = conflicting_result.get('confidence', 0)

    # Assert
    expected_confidence = max(0, base_confidence - mock_config['strategy_params']['fibo_strategy']['mta_confidence_modifier'])
    assert conflicting_confidence == expected_confidence, \
        f"Confidence with MTA conflict should be {expected_confidence}, but got {conflicting_confidence}"