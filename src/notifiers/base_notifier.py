from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    """Abstract base class for all notification services.

    This class defines a standard interface for sending messages and,
    optionally, for starting interactive sessions (like a polling bot).
    """

    def __init__(self, config: dict):
        """Initializes the notifier with its specific configuration.

        Args:
            config (dict): A dictionary containing configuration for the
                notifier (e.g., API tokens, chat IDs).
        """
        self.config = config

    @abstractmethod
    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Sends a simple text message.

        Args:
            message (str): The message content to send.
            parse_mode (str, optional): The parse mode for the message
                (e.g., 'HTML', 'Markdown'). Defaults to 'HTML'.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        pass

    def start(self):
        """Starts an interactive session (e.g., a polling bot).

        For notifiers that are send-only and do not support interactive
        sessions, this method is not intended to be used.

        Raises:
            NotImplementedError: If the specific notifier does not support
                an interactive session.
        """
        raise NotImplementedError("This notifier does not support an interactive session.")
