import logging
import traceback
from functools import wraps

class AnalysisErrorHandler:
    """A class to handle errors during financial analysis.

    This class provides a decorator to wrap analysis functions, catching and
    logging any exceptions that occur. It ensures that the application can
    continue to run even if some analyses fail.
    """

    def __init__(self):
        """Initializes the AnalysisErrorHandler."""
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def safe_analysis(self, func):
        """A decorator to protect analysis functions from errors.

        Args:
            func (callable): The analysis function to wrap.

        Returns:
            callable: The wrapped function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)

                # فحص النتيجة
                if result is None:
                    self.logger.warning(f"{func.__name__} returned None")
                    return self._get_default_result()

                if isinstance(result, dict) and not result:
                    self.logger.warning(f"{func.__name__} returned empty dict")
                    return self._get_default_result()

                return result

            except KeyError as e:
                self.logger.error(f"Column access error in {func.__name__}: {e}")
                self.logger.error("Check that DataFrame contains the required columns")
                return self._get_default_result()

            except NameError as e:
                self.logger.error(f"Function not found in {func.__name__}: {e}")
                self.logger.error("Check that all required functions are imported")
                return self._get_default_result()

            except Exception as e:
                self.logger.error(f"Unexpected error in {func.__name__}: {e}")
                self.logger.debug(traceback.format_exc())
                return self._get_default_result()

        return wrapper

    def _get_default_result(self):
        """Returns a default result when an analysis fails.

        This ensures that the system has a consistent output format even in
        case of an error.

        Returns:
            dict: A dictionary with default values for an analysis result.
        """
        return {
            'analysis_status': 'failed',
            'error_occurred': True,
            'signals': [],
            'patterns': [],
            'support_levels': [],
            'resistance_levels': [],
            'confidence': 0,
            'message': 'Analysis failed due to data or configuration issues'
        }

# إنشاء instance عام للاستخدام
error_handler = AnalysisErrorHandler()
