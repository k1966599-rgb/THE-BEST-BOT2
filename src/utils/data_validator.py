import pandas as pd
import logging

class DataValidator:
    """
    نظام فحص البيانات قبل التحليل
    يضمن صحة البيانات ووجود الأعمدة المطلوبة
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']

    def validate_dataframe(self, df, min_rows=30, analysis_type="general"):
        """
        فحص شامل لصحة DataFrame

        Args:
            df: DataFrame للفحص
            min_rows: الحد الأدنى لعدد الصفوف
            analysis_type: نوع التحليل المطلوب

        Returns:
            tuple: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # فحص الوجود والنوع
        if df is None:
            errors.append("DataFrame is None")
            return False, errors, warnings

        if not isinstance(df, pd.DataFrame):
            errors.append("Data is not a pandas DataFrame")
            return False, errors, warnings

        # فحص عدد الصفوف
        if len(df) < min_rows:
            errors.append(f"Insufficient data: {len(df)} rows, need at least {min_rows}")

        # فحص الأعمدة المطلوبة
        basic_columns = ['open', 'high', 'low', 'close']
        missing_basic = [col for col in basic_columns if col not in df.columns]
        if missing_basic:
            errors.append(f"Missing essential columns: {missing_basic}")

        # فحص القيم المفقودة
        for col in basic_columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                null_pct = null_count / len(df)
                if null_pct > 0.1:
                    warnings.append(f"High null percentage in {col}: {null_pct:.1%} ({null_count} values)")

        # فحص منطقية الأسعار
        if all(col in df.columns for col in ['high', 'low', 'open', 'close']):
            # فحص أن high >= low
            invalid_high_low = (df['high'] < df['low']).sum()
            if invalid_high_low > 0:
                errors.append(f"Invalid price data: {invalid_high_low} rows where high < low")

            # فحص أن الأسعار موجبة
            negative_prices = ((df['high'] <= 0) | (df['low'] <= 0) |
                             (df['open'] <= 0) | (df['close'] <= 0)).sum()
            if negative_prices > 0:
                errors.append(f"Invalid price data: {negative_prices} rows with non-positive prices")

        # فحص التسلسل الزمني
        if 'timestamp' in df.columns:
            if not df['timestamp'].is_monotonic_increasing:
                warnings.append("Timestamp column is not properly sorted")

        # فحص الحجم
        if 'volume' in df.columns:
            zero_volume = (df['volume'] == 0).sum()
            if zero_volume > len(df) * 0.1:
                warnings.append(f"High number of zero volume periods: {zero_volume}")

        # فحص خاص بنوع التحليل
        if analysis_type == "patterns" and len(df) < 50:
            warnings.append("Limited data for pattern analysis - results may be less reliable")

        if analysis_type == "indicators" and len(df) < 100:
            warnings.append("Limited data for technical indicators - some indicators may have many NaN values")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def log_validation_results(self, is_valid, errors, warnings, context=""):
        """
        تسجيل نتائج الفحص في السجلات
        """
        prefix = f"[{context}] " if context else ""

        if is_valid:
            self.logger.info(f"{prefix}Data validation passed")
        else:
            self.logger.error(f"{prefix}Data validation failed:")
            for error in errors:
                self.logger.error(f"  ERROR: {error}")

        for warning in warnings:
            self.logger.warning(f"  WARNING: {warning}")

        return is_valid

    def quick_column_check(self, df):
        """
        فحص سريع لأسماء الأعمدة
        """
        if df is None:
            return False

        required = ['open', 'high', 'low', 'close']
        available = df.columns.tolist()
        missing = [col for col in required if col not in available]

        if missing:
            self.logger.error(f"Missing columns: {missing}")
            self.logger.info(f"Available columns: {available}")
            return False

        return True

# إنشاء instance عام للاستخدام
data_validator = DataValidator()
