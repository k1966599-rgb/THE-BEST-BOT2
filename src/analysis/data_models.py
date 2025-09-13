from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Level:
    """Represents a single support or resistance level.

    Attributes:
        name (str): The name of the level (e.g., "Fibonacci Support 0.618",
            "Major Resistance").
        value (float): The price value of the level.
        level_type (str): The type of the level, either 'support' or
            'resistance'.
        quality (Optional[str]): The quality or strength of the level
            (e.g., "Strong", "Critical", "Historic"). Defaults to None.
    """
    name: str
    value: float
    level_type: str
    quality: Optional[str] = None

@dataclass
class Pattern:
    """Represents a detected technical pattern.

    Attributes:
        name (str): The name of the pattern (e.g., "Bull Flag").
        status (str): The current status of the pattern (e.g., "Forming",
            "Active", "Failed").
        timeframe (str): The timeframe in which the pattern was detected.
        activation_level (float): The price level at which the pattern is
            considered active or confirmed.
        invalidation_level (float): The price level at which the pattern is
            considered invalid.
        target1 (float): The first price target for the pattern.
        target2 (Optional[float]): The second price target. Defaults to None.
        target3 (Optional[float]): The third price target. Defaults to None.
        confidence (float): A score representing the confidence in the
            pattern's validity (0-100). Defaults to 50.0.
        raw_data (Dict[str, Any]): A dictionary containing any additional raw
            data or context about the pattern. Defaults to an empty dict.
    """
    name: str
    status: str
    timeframe: str

    # Core price points
    activation_level: float
    invalidation_level: float

    # Targets
    target1: float
    target2: Optional[float] = None
    target3: Optional[float] = None

    # Quality Score
    confidence: float = 50.0

    # Additional context
    raw_data: Dict[str, Any] = field(default_factory=dict)
