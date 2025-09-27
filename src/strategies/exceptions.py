# -*- coding: utf-8 -*-

class InsufficientDataError(Exception):
    """
    Custom exception raised when there is not enough data to perform a strategy analysis.

    This is typically raised after indicator calculations and data cleaning,
    indicating that the remaining data points are below the required threshold for a meaningful analysis.
    """
    pass