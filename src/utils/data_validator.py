import pandas as pd
import logging

class DataValidator:
    """A class for validating trading data before analysis.

    This class provides methods to ensure that the data is clean, contains the
    necessary columns, and is logically consistent.
    """

    def __init__(self):
        """Initializes the DataValidator."""
        self.logger = logging.getLogger(__name__)
        self.required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']

    def validate_dataframe(self, df, min_rows=30, analysis_type="general"):
        """Performs a comprehensive validation of a trading DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame to validate.
            min_rows (int, optional): The minimum number of rows required.
                Defaults to 30.
            analysis_type (str, optional): The type of analysis to be performed.
                This can affect the validation rules. Defaults to "general".

        Returns:
            tuple: A tuple containing:
                - bool: True if the DataFrame is valid, False otherwise.
                - list: A list of error messages.
                - list: A list of warning messages.
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
        """Logs the results of a data validation check.

        Args:
            is_valid (bool): Whether the data validation passed.
            errors (list): A list of error messages.
            warnings (list): A list of warning messages.
            context (str, optional): A string to provide context to the log
                messages. Defaults to "".

        Returns:
            bool: The value of is_valid.
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
        """Performs a quick check for the presence of required columns.

        Args:
            df (pd.DataFrame): The DataFrame to check.

        Returns:
            bool: True if all required columns are present, False otherwise.
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
