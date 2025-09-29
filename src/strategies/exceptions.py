# -*- coding: utf-8 -*-

class InsufficientDataError(Exception):
    """
    Custom exception raised when there is not enough data to perform a strategy analysis.

    This is typically raised after indicator calculations and data cleaning,
    indicating that the remaining data points are below the required threshold for a meaningful analysis.

    Attributes:
        required (int, optional): The number of data points required for the analysis.
        available (int, optional): The number of data points available after processing.
    """
    def __init__(self, message, required=None, available=None):
        super().__init__(message)
        self.required = required
        self.available = available