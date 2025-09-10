from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class TradeSetup:
    """
    Data class to hold all information about a potential trade setup.
    """
    # --- Core Pattern Info ---
    chat_id: int
    symbol: str
    timeframe: str
    pattern_name: str
    pattern_status: str  # e.g., 'قيد التكوين', 'مكتمل'

    # --- Primary Trade Parameters ---
    entry_price: float
    stop_loss: float
    target1: float
    target2: Optional[float] = None

    # --- Confirmed Entry Details ---
    confirmation_status: str = "🟡 في انتظار الاختراق"  # '✅ مفعل', '❌ فشل'
    confirmation_conditions: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)

    # --- Additional Context ---
    raw_pattern_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Set default conditions after the object is created.
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
