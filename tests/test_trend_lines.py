import pandas as pd
import pytest
from src.analysis.trend_lines import TrendLineAnalysis
from src.config import get_config
import numpy as np

@pytest.fixture
def trend_line_analysis_instance():
    config = get_config()
    analysis_config = config.get('analysis', {})
    return TrendLineAnalysis(config=analysis_config)

def test_trend_line_with_time_gaps(trend_line_analysis_instance, mocker):
    """
    Tests if the trend line calculation is correct when there are gaps in the
    DatetimeIndex, which simulates market closures or missing data.
    The buggy version uses integer indices for x-coordinates, leading to an
    incorrect slope. The fixed version should use the timestamps.
    """
    data = {
        'timestamp': pd.to_datetime([
            '2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 12:00',
            '2023-01-03 10:00', '2023-01-03 11:00', '2023-01-03 12:00',
            '2023-01-05 10:00', '2023-01-05 11:00', '2023-01-05 12:00', '2023-01-05 13:00',
        ]),
        'high': [120, 120, 120, 130, 130, 130, 140, 140, 140, 150],
        'low':  [110, 100, 110, 120, 120, 120, 130, 120, 130, 140],
        'close': [115, 105, 115, 125, 125, 125, 135, 125, 135, 145]
    }
    df = pd.DataFrame(data).set_index('timestamp')

    # Add more data to meet the minimum length requirement of the analyze method
    for i in range(15):
        new_timestamp = df.index[-1] + pd.Timedelta(hours=i+1)
        new_data = {
            'high': df['high'].iloc[-1] + 5,
            'low': df['low'].iloc[-1] + 5,
            'close': df['close'].iloc[-1] + 5
        }
        df.loc[new_timestamp] = new_data

    # Use all data
    trend_line_analysis_instance.long_period = len(df)

    # --- Correct Calculation ---
    pivots_df = pd.DataFrame({
        'x': df.index.astype(np.int64),
        'y': df['low'].values
    })
    p1 = (pivots_df['x'].iloc[1], pivots_df['y'].iloc[1])
    p2 = (pivots_df['x'].iloc[7], pivots_df['y'].iloc[7])

    slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
    intercept = p1[1] - slope * p1[0]

    current_time_x = df.index[-1].value
    correct_support_price = slope * current_time_x + intercept

    # --- Buggy Calculation ---
    p1_buggy = (1, df['low'].iloc[1])
    p2_buggy = (7, df['low'].iloc[7])

    slope_buggy = (p2_buggy[1] - p1_buggy[1]) / (p2_buggy[0] - p1_buggy[0])
    intercept_buggy = p1_buggy[1] - slope_buggy * p1_buggy[0]

    current_time_x_buggy = len(df) - 1
    buggy_support_price = slope_buggy * current_time_x_buggy + intercept_buggy

    # --- Run Analysis ---
    # Mock _get_pivots to ensure it returns the pivots we expect for the test
    mocker.patch.object(trend_line_analysis_instance, '_get_pivots', return_value=([], [1, 7]))
    result = trend_line_analysis_instance.analyze(df)

    assert len(result['supports']) == 1
    analyzed_support_price = result['supports'][0].value

    assert analyzed_support_price != pytest.approx(buggy_support_price)
    assert analyzed_support_price == pytest.approx(correct_support_price)
