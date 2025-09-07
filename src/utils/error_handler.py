import logging
import traceback
from functools import wraps

class AnalysisErrorHandler:
    """
    نظام معالجة الأخطاء للتحليل المالي
    يوفر معالجة شاملة للأخطاء مع تسجيل مفصل
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def safe_analysis(self, func):
        """
        decorator لحماية دوال التحليل من الأخطاء
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
        """
        إرجاع نتيجة افتراضية عند فشل التحليل
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
