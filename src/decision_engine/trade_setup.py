from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class TradeSetup:
    """Holds all information about a potential trade setup."""
    # --- Core Pattern Info ---
    chat_id: int
    symbol: str
    timeframe: str
    pattern_name: str
    pattern_status: str

    # --- Primary Trade Parameters ---
    entry_price: float
    stop_loss: float
    target1: float
    target2: Optional[float] = None
    target3: Optional[float] = None

    # --- Confirmed Entry Details ---
    confirmation_status: str = "🟡 Waiting for breakout"
    confirmation_rule: Optional[str] = None # e.g., '3_candle_close'
    confirmation_candles_closed: int = 0 # Counter for the monitor
    confirmation_conditions: List[str] = field(default_factory=list)
    optional_confirmation_conditions: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)

    # --- Additional Context ---
    raw_pattern_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.invalidation_conditions:
            self.invalidation_conditions = [
                f"Support Break: If a candle closes below ${self.stop_loss:,.2f} on the {self.timeframe} timeframe.",
                "Indicator Weakness: If indicators drop below (2/5).",
                "Timeout: If the breakout does not occur within 7 days.",
                f"Trend Change: If the trend shifts from sideways to bearish on the {self.timeframe} timeframe."
            ]
        if not self.target2:
            self.target2 = self.target1 * 1.02 if self.target1 > 0 else 0
