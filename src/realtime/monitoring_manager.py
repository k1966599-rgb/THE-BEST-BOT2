import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MonitoringManager:
    """
    The brain of the monitoring system. It keeps track of which analyses
    the user wants to monitor and checks incoming prices against their key levels.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton pattern to ensure only one instance of the manager exists
        if not cls._instance:
            cls._instance = super(MonitoringManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # This check ensures __init__ is only called once
        if not hasattr(self, 'initialized'):
            self.monitored_analyses: Dict[str, Dict[str, Any]] = {}
            self.initialized = True
            logger.info("MonitoringManager initialized.")

    def add_monitoring(self, symbol: str, analysis_data: Dict[str, Any], alert_chat_id: int):
        """
        Adds a new analysis to the monitoring list.
        """
        key_levels = {
            "fib_618": analysis_data.get("retracements", {}).get("fib_618"),
            "target": analysis_data.get("scenarios", {}).get("scenario1", {}).get("target"),
            "stop_loss": analysis_data.get("scenarios", {}).get("scenario1", {}).get("stop_loss")
        }

        self.monitored_analyses[symbol] = {
            "levels": {k: v for k, v in key_levels.items() if v is not None},
            "chat_id": alert_chat_id,
            "last_alert_level": None # To avoid spamming alerts for the same level
        }
        logger.info(f"Now monitoring {symbol} for chat_id {alert_chat_id}. Levels: {self.monitored_analyses[symbol]['levels']}")

    def remove_monitoring(self, symbol: str):
        """
        Removes an analysis from the monitoring list.
        """
        if symbol in self.monitored_analyses:
            del self.monitored_analyses[symbol]
            logger.info(f"Stopped monitoring {symbol}.")

    def check_price(self, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        """
        Checks if the current price for a symbol is near any of its monitored levels.
        """
        alerts = []
        analysis = self.monitored_analyses.get(symbol)

        if not analysis:
            return alerts

        for level_name, level_price in analysis["levels"].items():
            # Check if price is within a small tolerance (e.g., 0.5%) of the level
            if abs(current_price - level_price) / level_price <= 0.005:
                # Avoid sending repeated alerts for the same level crossing
                if analysis["last_alert_level"] != level_name:
                    alerts.append({
                        "symbol": symbol,
                        "level_name": level_name,
                        "level_price": level_price,
                        "current_price": current_price,
                        "chat_id": analysis["chat_id"]
                    })
                    analysis["last_alert_level"] = level_name
                    # If target or stop-loss is hit, we can stop monitoring
                    if level_name in ["target", "stop_loss"]:
                        self.remove_monitoring(symbol)
                        logger.info(f"Target/Stop-loss hit for {symbol}. Automatically removing from monitoring.")

        return alerts

# Global instance
monitoring_manager = MonitoringManager()