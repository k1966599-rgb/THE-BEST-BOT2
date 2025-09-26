"""
Custom exception classes for the application.
"""

class BotBaseException(Exception):
    """A base class for all custom exceptions in this application."""
    pass

class DataUnavailableError(BotBaseException):
    """
    Raised when historical market data cannot be fetched or is empty.
    """
    pass

class AnalysisError(BotBaseException):
    """
    Raised when an error occurs during the execution of a strategy's analysis,
    for example, due to insufficient data points after indicator calculation.
    """
    pass