import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def with_retry(max_attempts: int = 3, backoff_factor: float = 1.5, exceptions: tuple = (Exception,)):
    """
    A decorator to automatically retry a function call upon failure.

    Args:
        max_attempts: The maximum number of times to try the function.
        backoff_factor: Multiplier for the delay between retries.
        exceptions: A tuple of exception types to catch and trigger a retry.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"Function '{func.__name__}' failed after {max_attempts} attempts. Final error: {e}")
                        raise

                    wait_time = backoff_factor ** attempts
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} for '{func.__name__}' failed with error: {e}. "
                        f"Retrying in {wait_time:.2f} seconds..."
                    )
                    time.sleep(wait_time)
        return wrapper
    return decorator