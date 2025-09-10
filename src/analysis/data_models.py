from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Level:
    """
    A standardized data model for a single support or resistance level.
    """
    name: str  # e.g., "دعم فيبو 0.618", "مقاومة رئيسية"
    value: float
    level_type: str  # 'support' or 'resistance'
    quality: Optional[str] = None  # e.g., "قوي", "حرج", "تاريخي"

@dataclass
class Pattern:
    """
    A standardized data model for a detected technical pattern.
    """
    name: str
    status: str  # e.g., "قيد التكوين", "مفعل", "فشل"
    timeframe: str

    # Core price points
    activation_level: float
    invalidation_level: float

    # Targets
    target1: float
    target2: Optional[float] = None
    target3: Optional[float] = None

    # Additional context
    raw_data: Dict[str, Any] = field(default_factory=dict)
