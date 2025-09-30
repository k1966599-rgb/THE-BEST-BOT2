import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from src.config import get_config
from src.localization import get_text, TEXTS
from src.telegram_bot import (
    start,
    bot_status,
    conv_handler,
    error_handler,
    post_init,
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Starts the Telegram bot."""
    # --- Diagnostic Logging ---
    try:
        ar_keys = TEXTS.get('ar', {}).keys()
        logger.info(f"DIAGNOSTIC: Loaded {len(ar_keys)} keys for 'ar' language.")
        # Log a few specific keys to confirm they exist
        logger.info(f"DIAGNOSTIC: 'start_header' key exists: {'start_header' in ar_keys}")
        logger.info(f"DIAGNOSTIC: 'button_analyze' key exists: {'button_analyze' in ar_keys}")
    except Exception as e:
        logger.error(f"DIAGNOSTIC: Error during key logging: {e}")
    # --- End Diagnostic Logging ---

    config = get_config()
    token = config.get('telegram', {}).get('TOKEN')
    if not token:
        logger.error(get_text("error_no_token"))
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).post_init(post_init).build()

    # It's important to load the config into bot_data for access in handlers
    application.bot_data['config'] = config

    # Add command and callback query handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(bot_status, pattern='^bot_status$'))

    # Add the conversation handler for the analysis flow
    application.add_handler(conv_handler)

    # Add the error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info(get_text("bot_starting_log"))
    application.run_polling()

if __name__ == '__main__':
    main()