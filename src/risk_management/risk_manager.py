import logging
from typing import Dict, Any

class RiskManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('risk_management', {})
        self.logger = logging.getLogger(__name__)
        self.atr_multiplier_sl = self.config.get('atr_multiplier_sl', 2.0)
        self.atr_multiplier_tp = self.config.get('atr_multiplier_tp', 4.0)

    def calculate_sl_tp(self, entry_price: float, atr: float, signal: str) -> Dict[str, float]:
        """
        Calculates Stop-Loss and Take-Profit levels based on ATR.

        Args:
            entry_price (float): The price at which the trade is entered.
            atr (float): The current Average True Range value.
            signal (str): The signal type ('BUY' or 'SELL').

        Returns:
            Dict[str, float]: A dictionary with 'stop_loss' and 'take_profit' prices.
        """
        if signal == 'BUY':
            stop_loss = entry_price - (self.atr_multiplier_sl * atr)
            take_profit = entry_price + (self.atr_multiplier_tp * atr)
        elif signal == 'SELL':
            stop_loss = entry_price + (self.atr_multiplier_sl * atr)
            take_profit = entry_price - (self.atr_multiplier_tp * atr)
        else:
            return {}

        return {'stop_loss': stop_loss, 'take_profit': take_profit}


    def assess_risk(self, position: Dict[str, Any]):
        """
        Assess the risk of a given position.
        This is a placeholder for more complex risk management logic.
        """
        max_drawdown = self.config.get('max_drawdown', 100)
        if position.get('unrealized_pnl', 0) < -max_drawdown:
            self.logger.warning(f"Position {position.get('id')} has exceeded max drawdown.")
            return 'CLOSE'
        return 'HOLD'
