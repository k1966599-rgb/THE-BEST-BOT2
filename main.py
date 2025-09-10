import argparse
import logging
import sys
import time

from src.config import get_config, WATCHLIST
from src.data.okx_fetcher import OKXDataFetcher
from src.notifiers.telegram_notifier import InteractiveTelegramBot

# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    The main entry point for the application.
    This version is streamlined to run the interactive Telegram bot.
    """
    parser = argparse.ArgumentParser(description='The Best Bot - Main Entry Point')
    parser.add_argument(
        'mode',
        choices=['interactive'],
        default='interactive',
        nargs='?', # Makes the argument optional
        help="The mode to run the application in. Only 'interactive' is supported."
    )
    args = parser.parse_args()

    if args.mode == 'interactive':
        logger.info("Starting in Interactive mode...")

        # --- Initialize Components ---
        config = get_config()
        fetcher = OKXDataFetcher()

        # The interactive bot now only needs the config and the fetcher
        interactive_bot = InteractiveTelegramBot(
            config=config,
            fetcher=fetcher,
        )

        # Start background data services before running the bot
        logger.info("🚀 Starting background data services for interactive bot...")
        okx_symbols = [s.replace('/', '-') for s in WATCHLIST]
        fetcher.start_data_services(okx_symbols)

        logger.info("⏳ Waiting 10 seconds for initial price data to populate...")
        time.sleep(10)
        logger.info("✅ Initial data ready.")

        try:
            interactive_bot.start()
        except Exception as e:
            logger.exception("An error occurred while running the bot.")
        finally:
            logger.info("⏹️ Stopping data services...")
            fetcher.stop()
            logger.info("Bot has been shut down.")
    else:
        logger.error(f"Mode '{args.mode}' is not supported in this version.")
        sys.exit(1)


if __name__ == "__main__":
    main()
