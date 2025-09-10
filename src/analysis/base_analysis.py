from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseAnalysis(ABC):
    """
    Abstract base class for all analysis modules. It defines a standard
    interface for analysis components.
    """

    def __init__(self, config: dict = None, timeframe: str = None):
        """
        Initializes the analysis module.

        :param config: A dictionary containing configuration for the analysis.
        :param timeframe: The timeframe being analyzed (e.g., '1h', '4h').
        """
        if config is None:
            config = {}
        self.config = config
        self.timeframe = timeframe

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs the specific analysis and returns the results.

        :return: A dictionary containing the analysis results, including a score
                 and other relevant details. Must include a 'total_score' or
                 a similarly named primary score key.
        """
        pass
