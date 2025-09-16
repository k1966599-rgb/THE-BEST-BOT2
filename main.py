import questionary
import time
import logging
import threading
from src.config import get_config
from src.core.engine import TradingEngine
from src.strategies.fibo_strategy import FiboStrategy

def run_trading_bot():
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


def analysis_menu():
    while True:
        currency = questionary.select(
            "Select a currency for analysis:",
            choices=["BTC", "ETH", "SOL", "LINK", "DOGE", "Back"]
        ).ask()

        if currency == "Back":
            break

        term = questionary.select(
            f"Select analysis term for {currency}:",
            choices=["Long Term", "Medium Term", "Short Term", "Back"]
        ).ask()

        if term == "Back":
            continue

        timeframe_map = {
            "Long Term": ["1D", "4H", "1H"],
            "Medium Term": ["30m", "15m"],
            "Short Term": ["5m", "3m"]
        }

        timeframe = questionary.select(
            f"Select timeframe for {term} analysis of {currency}:",
            choices=timeframe_map[term] + ["Back"]
        ).ask()

        if timeframe == "Back":
            continue

        questionary.print(f"Analysis for {currency} on {timeframe} timeframe.")
        # Here you would call the analysis function
        time.sleep(2)


bot_thread = None
bot_status = "متوقف"

def main_menu():
    """
    The main menu of the application.
    """
    global bot_thread, bot_status
    questionary.print("مرحباً THE BEST BOT")

    while True:
        # Check if the bot thread has finished (e.g., due to an error)
        if bot_thread and not bot_thread.is_alive() and bot_status == "يعمل":
            bot_status = "خطأ - توقف البوت" # Error - Bot stopped
            questionary.print(f"الحالة: {bot_status}", style="bold red")
        else:
            questionary.print(f"الحالة: {bot_status}")

        choices = ["تشغيل", "تحليل", "متابعة الصفقات"]
        # Add a "Stop" option if the bot is running
        if bot_status == "يعمل":
            # Stopping a thread gracefully is complex. For now, we just notify the user.
            # A real implementation would require a signaling mechanism (e.g., an event).
            choices.append("إيقاف (غير مدعوم بعد)")
        choices.append("Exit")

        choice = questionary.select(
            "Main Menu:",
            choices=choices
        ).ask()

        if choice == "تشغيل":
            if bot_status != "يعمل":
                questionary.print("Starting the trading bot in the background...")
                bot_status = "يعمل"
                bot_thread = threading.Thread(target=run_trading_bot, daemon=True)
                bot_thread.start()
                time.sleep(1) # Give the thread a moment to start
            else:
                questionary.print("Bot is already running.", style="bold italic")
        elif choice == "تحليل":
            analysis_menu()
        elif choice == "متابعة الصفقات":
            questionary.print("Feature not implemented yet.")
            time.sleep(2)
        elif choice == "Exit":
            questionary.print("Exiting... please note the bot may still be running in the background.")
            break

if __name__ == '__main__':
    main_menu()
