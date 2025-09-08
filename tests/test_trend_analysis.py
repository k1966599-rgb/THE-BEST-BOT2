import pytest
import pandas as pd
from src.analysis.trends import TrendAnalysis
from src.config import get_config

def generate_dummy_data(length):
    # ... (dummy data generation)
    pass

@pytest.fixture
def trend_analysis_instance():
    config = get_config()
    return TrendAnalysis(config=config.get('analysis'))

def test_uptrend_detection(trend_analysis_instance):
    df = pd.DataFrame({
        'close': [i for i in range(100, 200)],
        'EMA_20': [i - 5 for i in range(100, 200)],
        'EMA_50': [i - 10 for i in range(100, 200)],
        'EMA_100': [i - 15 for i in range(100, 200)],
        'ADX_14': [30] * 100
    })
    result = trend_analysis_instance.analyze(df)
    assert result['trend_direction'] == 'Uptrend'
