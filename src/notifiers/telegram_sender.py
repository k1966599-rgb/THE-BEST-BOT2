import requests
import logging
from typing import Dict

from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)

class SimpleTelegramNotifier(BaseNotifier):
    """A simple notifier for sending one-way messages to a Telegram chat.

    This class is used for sending non-interactive alerts and reports to a
    pre-configured Telegram chat ID using a bot token.
    """
    def __init__(self, config: Dict):
        """Initializes the SimpleTelegramNotifier.

        Args:
            config (Dict): A dictionary expected to contain 'BOT_TOKEN' and
                'CHAT_ID'.
        """
        super().__init__(config)
        self.token = self.config.get('BOT_TOKEN')
        self.chat_id = self.config.get('CHAT_ID')
        self.bot = None # Added for compatibility with TradeMonitor

    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Sends a message to the configured Telegram chat.

        This method handles sending messages via the Telegram Bot API. It also
        includes logic to automatically split messages that exceed Telegram's
        character limit.

        Args:
            message (str): The message content to send.
            parse_mode (str, optional): The parse mode for the message.
                Defaults to 'HTML'.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        if not self.token or not self.chat_id:
            logger.warning("Telegram BOT_TOKEN or CHAT_ID not configured. Skipping message.")
            return False

        message_preview = message.split('\n')[0]
        logger.info(f"Attempting to send report to Telegram: {message_preview}...")

        max_length = 4096
        try:
            # Construct the base URL
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"

            # Send the message(s)
            if len(message) <= max_length:
                params = {'chat_id': self.chat_id, 'text': message, 'parse_mode': parse_mode}
                response = requests.post(url, params=params, timeout=10)
                response.raise_for_status()
            else:
                # Split the message into parts if it's too long
                parts = []
                current_part = ""
                for line in message.split('\n'):
                    if len(current_part) + len(line) + 1 > max_length:
                        parts.append(current_part)
                        current_part = ""
                    current_part += line + "\n"
                if current_part:
                    parts.append(current_part)

                for i, part in enumerate(parts):
                    header = f"📊 <b>Analysis Report (Part {i+1}/{len(parts)})</b>\n\n"
                    params = {'chat_id': self.chat_id, 'text': header + part, 'parse_mode': parse_mode}
                    response = requests.post(url, params=params, timeout=10)
                    response.raise_for_status()

            logger.info("✅ Report sent successfully to Telegram.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.exception(f"❌ An unexpected error occurred while sending Telegram message.")
            return False
