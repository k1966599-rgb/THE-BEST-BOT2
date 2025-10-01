import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from src.config import get_config
from src.localization import get_text
from src.telegram_bot import (
    start,
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

    # Add the conversation handler for the analysis flow
    # This handler now manages the 'analyze_start' callback.
    application.add_handler(conv_handler)

    # Add the error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info(get_text("bot_starting_log"))
    application.run_polling()

if __name__ == '__main__':
    main()