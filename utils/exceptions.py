"""
Custom exceptions for Trading212 Tax Calculator.

This module defines a hierarchy of custom exceptions to provide
better error handling and more informative error messages.
"""


class TaxCalculatorError(Exception):
    """Base exception for all tax calculator errors"""
    
    def __init__(self, message: str, details: str = None):
        """
        Initialize TaxCalculatorError.
        
        Args:
            message: User-friendly error message
            details: Technical details for debugging (optional)
        """
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


# ============================================================================
# Input/Output Errors
# ============================================================================

class FileError(TaxCalculatorError):
    """Base class for file-related errors"""
    pass


class FileNotFoundError(FileError):
    """Raised when a required file is not found"""
    
    def __init__(self, file_path: str):
        message = f"File not found: {file_path}"
        details = "Please check that the file path is correct and the file exists."
        super().__init__(message, details)
        self.file_path = file_path


class FileReadError(FileError):
    """Raised when a file cannot be read"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"Cannot read file: {file_path}"
        details = reason or "Check file permissions and format."
        super().__init__(message, details)
        self.file_path = file_path


class FileWriteError(FileError):
    """Raised when a file cannot be written"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"Cannot write to file: {file_path}"
        details = reason or "Check directory permissions and disk space."
        super().__init__(message, details)
        self.file_path = file_path


# ============================================================================
# Data Validation Errors
# ============================================================================

class DataValidationError(TaxCalculatorError):
    """Base class for data validation errors"""
    pass


class InvalidCSVFormatError(DataValidationError):
    """Raised when CSV file has invalid format"""
    
    def __init__(self, file_path: str, missing_columns: list = None, reason: str = None):
        if missing_columns:
            message = f"Invalid CSV format in {file_path}: Missing required columns"
            details = f"Missing columns: {', '.join(missing_columns)}"
        else:
            message = f"Invalid CSV format in {file_path}"
            details = reason or "Expected Trading212 export format or processed CSV format."
        super().__init__(message, details)
        self.file_path = file_path
        self.missing_columns = missing_columns


class InvalidTransactionDataError(DataValidationError):
    """Raised when transaction data is invalid"""
    
    def __init__(self, row_number: int = None, field: str = None, value: str = None, reason: str = None):
        if row_number and field:
            message = f"Invalid transaction data at row {row_number}, field '{field}'"
            details = reason or f"Invalid value: {value}"
        else:
            message = "Invalid transaction data"
            details = reason or "Transaction data does not meet required format."
        super().__init__(message, details)
        self.row_number = row_number
        self.field = field
        self.value = value


class MissingRequiredFieldError(DataValidationError):
    """Raised when a required field is missing"""
    
    def __init__(self, field_name: str, context: str = None):
        message = f"Required field missing: {field_name}"
        details = context or "This field is required for tax calculations."
        super().__init__(message, details)
        self.field_name = field_name


# ============================================================================
# Parsing Errors
# ============================================================================

class ParsingError(TaxCalculatorError):
    """Base class for parsing errors"""
    pass


class DateParsingError(ParsingError):
    """Raised when a date cannot be parsed"""
    
    def __init__(self, date_string: str, expected_format: str = None):
        message = f"Cannot parse date: {date_string}"
        details = f"Expected format: {expected_format}" if expected_format else "Expected ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
        super().__init__(message, details)
        self.date_string = date_string


class NumberParsingError(ParsingError):
    """Raised when a number cannot be parsed"""
    
    def __init__(self, value: str, field_name: str = None):
        if field_name:
            message = f"Cannot parse number in field '{field_name}': {value}"
        else:
            message = f"Cannot parse number: {value}"
        details = "Expected a valid number (integer or decimal)."
        super().__init__(message, details)
        self.value = value
        self.field_name = field_name


# ============================================================================
# Service Errors
# ============================================================================

class ServiceError(TaxCalculatorError):
    """Base class for external service errors"""
    pass


class ExchangeRateError(ServiceError):
    """Raised when exchange rate cannot be retrieved"""
    
    def __init__(self, currency: str, date: str, reason: str = None):
        message = f"Cannot get exchange rate for {currency} on {date}"
        details = reason or "NBP API may be unavailable or the date is too far in the past."
        super().__init__(message, details)
        self.currency = currency
        self.date = date


class APIError(ServiceError):
    """Raised when an external API call fails"""
    
    def __init__(self, api_name: str, reason: str = None, status_code: int = None):
        message = f"API error: {api_name}"
        if status_code:
            details = f"HTTP {status_code}: {reason or 'Request failed'}"
        else:
            details = reason or "The API request failed. Check your internet connection."
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code


class CompanyInfoError(ServiceError):
    """Raised when company information cannot be retrieved"""
    
    def __init__(self, isin: str, reason: str = None):
        message = f"Cannot get company information for ISIN: {isin}"
        details = reason or "yfinance API may be unavailable. Country will be derived from ISIN."
        super().__init__(message, details)
        self.isin = isin


# ============================================================================
# Calculation Errors
# ============================================================================

class CalculationError(TaxCalculatorError):
    """Base class for calculation errors"""
    pass


class FIFOCalculationError(CalculationError):
    """Raised when FIFO calculation fails"""
    
    def __init__(self, ticker: str, reason: str):
        message = f"FIFO calculation error for {ticker}"
        details = reason
        super().__init__(message, details)
        self.ticker = ticker


class InsufficientSharesError(FIFOCalculationError):
    """Raised when trying to sell more shares than available"""
    
    def __init__(self, ticker: str, available: float, requested: float):
        message = f"Cannot sell {requested} shares of {ticker}"
        details = f"Only {available} shares available in portfolio. Check for missing buy transactions or incorrect transaction order."
        super().__init__(ticker, details)
        self.available = available
        self.requested = requested


class NegativeQuantityError(CalculationError):
    """Raised when a transaction has negative quantity"""
    
    def __init__(self, transaction_type: str, ticker: str, quantity: float):
        message = f"Invalid {transaction_type} transaction: negative quantity"
        details = f"Ticker: {ticker}, Quantity: {quantity}. Transaction quantities must be positive."
        super().__init__(message, details)
        self.ticker = ticker
        self.quantity = quantity


# ============================================================================
# Export Errors
# ============================================================================

class ExportError(TaxCalculatorError):
    """Base class for export errors"""
    pass


class ExcelExportError(ExportError):
    """Raised when Excel export fails"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"Cannot export to Excel: {file_path}"
        details = reason or "Check that the file is not open in another program and you have write permissions."
        super().__init__(message, details)
        self.file_path = file_path


class PDFExportError(ExportError):
    """Raised when PDF export fails"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"Cannot export to PDF: {file_path}"
        details = reason or "Check font availability and write permissions."
        super().__init__(message, details)
        self.file_path = file_path


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(TaxCalculatorError):
    """Base class for configuration errors"""
    pass


class MissingDependencyError(ConfigurationError):
    """Raised when a required dependency is missing"""
    
    def __init__(self, dependency_name: str, install_command: str = None):
        message = f"Missing required dependency: {dependency_name}"
        if install_command:
            details = f"Install with: {install_command}"
        else:
            details = f"Install with: pip install {dependency_name}"
        super().__init__(message, details)
        self.dependency_name = dependency_name


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid"""
    
    def __init__(self, config_key: str, reason: str):
        message = f"Invalid configuration: {config_key}"
        details = reason
        super().__init__(message, details)
        self.config_key = config_key


# ============================================================================
# Utility functions for error handling
# ============================================================================

def handle_file_not_found(file_path: str) -> FileNotFoundError:
    """
    Create a FileNotFoundError with helpful suggestions.
    
    Args:
        file_path: Path to the missing file
        
    Returns:
        FileNotFoundError instance
    """
    import os
    
    # Provide helpful suggestions based on file type
    if file_path.endswith('.csv'):
        suggestion = "Make sure you've exported your Trading212 transaction history as CSV."
    elif file_path.endswith('.env'):
        suggestion = "Create a .env file with your personal data (optional)."
    else:
        suggestion = "Check the file path and try again."
    
    error = FileNotFoundError(file_path)
    error.details = f"{error.details}\n{suggestion}"
    return error


def handle_parsing_error(row_number: int, field: str, value, original_error: Exception) -> InvalidTransactionDataError:
    """
    Create a parsing error with context.
    
    Args:
        row_number: Row number in CSV
        field: Field name that failed to parse
        value: Value that failed to parse
        original_error: Original exception
        
    Returns:
        InvalidTransactionDataError instance
    """
    return InvalidTransactionDataError(
        row_number=row_number,
        field=field,
        value=str(value),
        reason=f"{type(original_error).__name__}: {str(original_error)}"
    )
