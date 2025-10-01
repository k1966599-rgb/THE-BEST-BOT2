import pytest
import pandas as pd
from src.validators import DataValidator

def test_validate_and_clean_dataframe_success():
    """
    Tests that a valid list of candle data is correctly converted to a clean DataFrame.
    """
    raw_data = [
        {'timestamp': '1672531200000', 'open': '100', 'high': '110', 'low': '90', 'close': '105', 'volume': '1000'},
        {'timestamp': '1672534800000', 'open': '105', 'high': '115', 'low': '100', 'close': '110', 'volume': '1200'},
        # Duplicate timestamp to be dropped
        {'timestamp': '1672531200000', 'open': '100', 'high': '110', 'low': '90', 'close': '105', 'volume': '1000'},
        # Row with missing data to be dropped
        {'timestamp': '1672538400000', 'open': '110', 'high': '120', 'low': '105', 'close': None, 'volume': '1300'},
    ]

    df = DataValidator.validate_and_clean_dataframe(raw_data)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # Should drop duplicate and row with NaN
    assert df['timestamp'].is_monotonic_increasing
    assert df['close'].iloc[1] == 110

def test_validate_empty_data_raises_error():
    """
    Tests that passing empty data to the validator raises a ValueError.
    """
    with pytest.raises(ValueError, match="Input data for DataFrame creation cannot be empty"):
        DataValidator.validate_and_clean_dataframe([])

def test_validate_missing_columns_raises_error():
    """
    Tests that data with missing required columns raises a ValueError.
    """
    invalid_data = [
        {'timestamp': '1672531200000', 'open': '100', 'high': '110', 'low': '90'}, # Missing 'close' and 'volume'
    ]
    with pytest.raises(ValueError, match="Input data is missing one of the required columns"):
        DataValidator.validate_and_clean_dataframe(invalid_data)