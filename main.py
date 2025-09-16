import logging
from src.config import get_config
from src.core.engine import TradingEngine
from src.strategies.fibo_strategy import FiboStrategy
# To add a new strategy, you would import it here and instantiate it below.

def main():
    """
    The main entry point for the trading bot.
    """
    # --- 1. Configure Logging ---
    # Sets up basic logging to print to the console and a file.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("trading_bot.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Trading Bot ---")

    # --- 2. Load Configuration ---
    try:
        config = get_config()
        logger.info("Configuration loaded successfully.")
    except Exception as e:
        logger.exception(f"Failed to load configuration: {e}")
        return

    # --- 3. Initialize Strategy ---
    # Here you can choose which strategy to run.
    # This could be made configurable in config.py later.
    try:
        strategy = FiboStrategy(config)
        logger.info(f"Strategy loaded: {strategy.__class__.__name__}")
    except Exception as e:
        logger.exception(f"Failed to initialize strategy: {e}")
        return

    # --- 4. Initialize and Run the Trading Engine ---
    try:
        engine = TradingEngine(config=config, strategy=strategy)
        # The engine's run() method contains the main trading loop.
        engine.run()
    except Exception as e:
        logger.exception(f"The trading engine encountered a fatal error: {e}")
    finally:
        logger.info("--- Trading Bot Shutdown ---")

if __name__ == '__main__':
    main()
