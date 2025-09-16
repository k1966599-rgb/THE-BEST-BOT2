"""
This package contains all the individual analysis modules for the bot.
By importing the classes here, we make them easily accessible from the
top-level `analysis` package, simplifying imports in other parts of the application.
"""

from .base_analysis import BaseAnalysis
from .trends import TrendAnalysis
from .quantile_channel_analysis import QuantileChannelAnalysis
from .new_support_resistance import NewSupportResistanceAnalysis
from .fibonacci import FibonacciAnalysis
from .classic_patterns import ClassicPatterns
from .orchestrator import AnalysisOrchestrator
