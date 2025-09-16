"""
This package contains all the individual analysis modules for the bot.
By importing the classes here, we make them easily accessible from the
top-level `analysis` package, simplifying imports in other parts of the application.
"""

from .base_analysis import BaseAnalysis
from .classic_patterns import ClassicPatterns
from .fibonacci import FibonacciAnalysis
from .new_support_resistance import NewSupportResistanceAnalysis
from .orchestrator import AnalysisOrchestrator
from .pivot_detector import PivotDetector
from .quantile_channel_analysis import QuantileChannelAnalysis
from .trends import TrendAnalysis
