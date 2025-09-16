import logging

class RiskManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def assess_risk(self, position):
        """
        Assess the risk of a given position.
        This is a placeholder for more complex risk management logic.
        """
        if position['unrealized_pnl'] < -self.config.get('max_drawdown', 100):
            self.logger.warning(f"Position {position['id']} has exceeded max drawdown.")
            return 'CLOSE'
        return 'HOLD'
