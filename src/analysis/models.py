from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class TechnicalPattern:
    """Represents a technical pattern identified in a timeframe."""
    name: str
    status: str  # e.g., 'قيد التكوين', 'مفعل', 'فشل'
    activation_condition: str
    invalidation_condition: str
    target: Optional[float] = None

@dataclass
class Support:
    """Represents a support level."""
    type: str
    level: float
    strength: str

@dataclass
class Resistance:
    """Represents a resistance level."""
    type: str
    level: float
    strength: str

@dataclass
class TimeframeAnalysis:
    """Holds the analysis for a specific timeframe (e.g., 1H, 4H)."""
    timeframe: str
    current_price: float
    pattern: TechnicalPattern
    supports: List[Support] = field(default_factory=list)
    resistances: List[Resistance] = field(default_factory=list)

@dataclass
class ExecutiveSummary:
    """Holds the summary for different time horizons."""
    short_term_summary: str
    medium_term_summary: str
    long_term_summary: str
    critical_points: Dict[str, str]

@dataclass
class ConfirmedTrade:
    """Represents a potential trade setup based on the analysis."""
    entry_price_condition: str
    targets: List[float]
    stop_loss_condition: str
    strategy_details: str

@dataclass
class AnalysisReport:
    """The main container for a full technical analysis report."""
    report_id: str
    pair: str
    platform: str = "OKX Exchange"
    timestamp: datetime = field(default_factory=datetime.now)
    analysis_type: str = "استثمار طويل المدى"
    timeframe_analyses: List[TimeframeAnalysis] = field(default_factory=list)
    summary: Optional[ExecutiveSummary] = None
    confirmed_trade: Optional[ConfirmedTrade] = None
    is_followed: bool = False
