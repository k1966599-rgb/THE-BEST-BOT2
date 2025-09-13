"""
This package contains all the individual analysis modules for the bot.
By importing the classes here, we make them easily accessible from the
top-level `analysis` package, simplifying imports in other parts of the application.
"""

from .base_analysis import BaseAnalysis
from .technical_score import TechnicalIndicators
from .trends import TrendAnalysis
from .trend_lines import TrendLineAnalysis
from .channels import PriceChannels
from .support_resistance import SupportResistanceAnalysis
from .fibonacci import FibonacciAnalysis
from .volume_profile import VolumeProfileAnalysis
from .classic_patterns import ClassicPatterns
from .orchestrator import AnalysisOrchestrator
