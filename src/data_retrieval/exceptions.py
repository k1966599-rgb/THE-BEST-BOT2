class DataFetcherError(Exception):
    """Base exception class for DataFetcher errors."""
    pass

class APIError(DataFetcherError):
    """Raised for errors coming from the exchange API."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class NetworkError(DataFetcherError):
    """Raised for network-related errors (e.g., connection timeout)."""
    pass