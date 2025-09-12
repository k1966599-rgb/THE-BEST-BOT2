from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class TradeSetup:
    """Holds all information about a potential trade setup.

    This data class encapsulates everything needed to monitor, execute, and
    manage a trade based on a detected technical pattern.

    Attributes:
        chat_id (int): The identifier for the chat associated with this setup.
        symbol (str): The trading symbol (e.g., 'BTC-USDT').
        timeframe (str): The timeframe on which the pattern was detected.
        pattern_name (str): The name of the detected pattern.
        pattern_status (str): The current status of the pattern (e.g., 'Forming').
        entry_price (float): The target price for trade entry.
        stop_loss (float): The price at which to exit the trade at a loss.
        target1 (float): The first profit target.
        target2 (Optional[float]): The second profit target.
        confirmation_status (str): The current status of the trade confirmation
            (e.g., 'Waiting for breakout').
        confirmation_conditions (List[str]): A list of conditions required
            to confirm the trade entry.
        invalidation_conditions (List[str]): A list of conditions that would
            invalidate the trade setup.
        raw_pattern_data (Dict[str, Any]): The raw dictionary of data from the
            detected pattern object.
    """
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

    # --- Confirmed Entry Details ---
    confirmation_status: str = "🟡 في انتظار الاختراق"
    confirmation_conditions: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)

    # --- Additional Context ---
    raw_pattern_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Sets default values after the object is initialized.

        This method provides default invalidation conditions and calculates a
        default second target if they are not explicitly provided.
        """
        if not self.invalidation_conditions:
            self.invalidation_conditions = [
                f"كسر الدعم: إذا أغلقت شمعة تحت ${self.stop_loss:,.2f} على فريم {self.timeframe}",
                "ضعف المؤشرات: إذا انخفضت المؤشرات تحت (2/5)",
                "انتهاء المهلة: إذا لم يحدث الاختراق خلال 7 أيام",
                f"تغيير الترند: إذا تحول الترند من عرضي إلى هابط على فريم {self.timeframe}"
            ]

        if not self.target2:
            self.target2 = self.target1 * 1.02 if self.target1 > 0 else 0
