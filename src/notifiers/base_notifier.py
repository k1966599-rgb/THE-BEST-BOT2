from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    """
    Abstract base class for all notification services. It defines a standard
    interface for sending messages or starting interactive sessions.
    """

    def __init__(self, config: dict):
        """
        Initializes the notifier with its specific configuration.

        :param config: A dictionary containing configuration for the notifier
                       (e.g., API tokens, chat IDs).
        """
        self.config = config

    @abstractmethod
    def send(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Sends a simple text message.

        :param message: The message content to send.
        :param parse_mode: The parse mode for the message (e.g., 'HTML', 'Markdown').
        :return: True if the message was sent successfully, False otherwise.
        """
        pass

    def start(self):
        """
        Starts an interactive session (e.g., a polling bot).
        For notifiers that do not support interactive sessions, this method
        can be left unimplemented or raise a NotImplementedError.
        """
        raise NotImplementedError("This notifier does not support an interactive session.")
