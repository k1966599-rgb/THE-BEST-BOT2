from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseAnalysis(ABC):
    """Abstract base class for all analysis modules.

    This class defines the standard interface for all analysis components,
    ensuring that each analysis module implements the required methods.
    """

    def __init__(self, config: dict = None, timeframe: str = None):
        """Initializes the base analysis module.

        Args:
            config (dict, optional): A dictionary containing configuration
                settings for the analysis. Defaults to None.
            timeframe (str, optional): The timeframe for the data being
                analyzed (e.g., '1h', '4h', '1d'). Defaults to None.
        """
        if config is None:
            config = {}
        self.config = config
        self.timeframe = timeframe
        self.params = self._get_timeframe_specific_params()

    def _get_timeframe_specific_params(self) -> Dict[str, Any]:
        """
        Retrieves the specific analysis parameters for the module's timeframe.
        """
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        timeframe_group = 'default' # Fallback group
        for group, timeframes in timeframe_groups.items():
            if self.timeframe in timeframes:
                timeframe_group = group
                break

        # Load the params for the identified group
        analysis_groups = self.config.get('analysis', {}).get('groups', {})
        return analysis_groups.get(timeframe_group, {})

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Runs the specific analysis on the given DataFrame.

        This method must be implemented by all subclasses. It should perform
        the analysis and return a dictionary of results.

        Args:
            df (pd.DataFrame): The DataFrame containing the market data to be
                analyzed. It should have columns like 'open', 'high', 'low',
                'close', and 'volume'.

        Returns:
            Dict[str, Any]: A dictionary containing the analysis results. The
            dictionary should include a primary score key (e.g., 'total_score')
            and any other relevant details.

        Raises:
            NotImplementedError: If the method is not implemented by the
                subclass.
        """
        pass
