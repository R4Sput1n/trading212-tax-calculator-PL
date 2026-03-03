"""
Tests for custom exception classes
"""
import pytest
from utils.exceptions import (
    TaxCalculatorError,
    FileNotFoundError,
    FileReadError,
    FileWriteError,
    InvalidCSVFormatError,
    InvalidTransactionDataError,
    DateParsingError,
    NumberParsingError,
    ExchangeRateError,
    APIError,
    InsufficientSharesError,
    FIFOCalculationError,
    ExcelExportError,
    PDFExportError,
    handle_file_not_found,
    handle_parsing_error
)


class TestBaseException:
    """Tests for TaxCalculatorError base class"""
    
    def test_base_exception_with_message_only(self):
        """Test creating exception with just a message"""
        exc = TaxCalculatorError("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.details is None
        assert str(exc) == "Something went wrong"
    
    def test_base_exception_with_details(self):
        """Test creating exception with message and details"""
        exc = TaxCalculatorError("Something went wrong", "Technical details here")
        assert exc.message == "Something went wrong"
        assert exc.details == "Technical details here"
        assert "Something went wrong" in str(exc)
        assert "Technical details here" in str(exc)


class TestFileExceptions:
    """Tests for file-related exceptions"""
    
    def test_file_not_found_error(self):
        """Test FileNotFoundError"""
        exc = FileNotFoundError("/path/to/file.csv")
        assert "file.csv" in exc.message.lower()
        assert exc.file_path == "/path/to/file.csv"
        assert exc.details is not None
    
    def test_file_read_error_with_reason(self):
        """Test FileReadError with custom reason"""
        exc = FileReadError("/path/to/file.csv", "Permission denied")
        assert "file.csv" in exc.message
        assert "Permission denied" in exc.details
        assert exc.file_path == "/path/to/file.csv"
    
    def test_file_write_error(self):
        """Test FileWriteError"""
        exc = FileWriteError("/path/to/output.xlsx")
        assert "output.xlsx" in exc.message
        assert exc.file_path == "/path/to/output.xlsx"


class TestDataValidationExceptions:
    """Tests for data validation exceptions"""
    
    def test_invalid_csv_format_with_missing_columns(self):
        """Test InvalidCSVFormatError with missing columns"""
        missing = ["Action", "Time", "Ticker"]
        exc = InvalidCSVFormatError("data.csv", missing_columns=missing)
        assert "data.csv" in exc.message
        assert exc.file_path == "data.csv"
        assert exc.missing_columns == missing
        assert "Action" in exc.details
    
    def test_invalid_transaction_data_with_details(self):
        """Test InvalidTransactionDataError with full details"""
        exc = InvalidTransactionDataError(
            row_number=42,
            field="quantity",
            value="abc",
            reason="Not a number"
        )
        assert "42" in exc.message
        assert "quantity" in exc.message
        assert exc.row_number == 42
        assert exc.field == "quantity"


class TestParsingExceptions:
    """Tests for parsing exceptions"""
    
    def test_date_parsing_error(self):
        """Test DateParsingError"""
        exc = DateParsingError("2024-13-45", "YYYY-MM-DD")
        assert "2024-13-45" in exc.message
        assert "YYYY-MM-DD" in exc.details
        assert exc.date_string == "2024-13-45"
    
    def test_number_parsing_error(self):
        """Test NumberParsingError"""
        exc = NumberParsingError("abc123", "price")
        assert "abc123" in exc.message
        assert "price" in exc.message
        assert exc.value == "abc123"
        assert exc.field_name == "price"


class TestServiceExceptions:
    """Tests for service-related exceptions"""
    
    def test_exchange_rate_error(self):
        """Test ExchangeRateError"""
        exc = ExchangeRateError("USD", "2024-01-15", "API unavailable")
        assert "USD" in exc.message
        assert "2024-01-15" in exc.message
        assert "API unavailable" in exc.details
        assert exc.currency == "USD"
        assert exc.date == "2024-01-15"
    
    def test_api_error_with_status_code(self):
        """Test APIError with HTTP status code"""
        exc = APIError("NBP API", "Service unavailable", 503)
        assert "NBP API" in exc.message
        assert exc.status_code == 503
        assert "503" in exc.details


class TestCalculationExceptions:
    """Tests for calculation exceptions"""
    
    def test_insufficient_shares_error(self):
        """Test InsufficientSharesError"""
        exc = InsufficientSharesError("AAPL", 10.0, 15.0)
        assert "AAPL" in exc.message
        assert exc.ticker == "AAPL"
        assert exc.available == 10.0
        assert exc.requested == 15.0
        assert "10" in exc.details or "10.0" in exc.details
        # The details field contains the message, so checking for available shares is sufficient
    
    def test_fifo_calculation_error(self):
        """Test FIFOCalculationError"""
        exc = FIFOCalculationError("AAPL", "Cannot match transactions")
        assert "AAPL" in exc.message
        assert "Cannot match transactions" in exc.details
        assert exc.ticker == "AAPL"


class TestExportExceptions:
    """Tests for export exceptions"""
    
    def test_excel_export_error(self):
        """Test ExcelExportError"""
        exc = ExcelExportError("report.xlsx", "File is open")
        assert "report.xlsx" in exc.message
        assert "File is open" in exc.details
        assert exc.file_path == "report.xlsx"
    
    def test_pdf_export_error(self):
        """Test PDFExportError"""
        exc = PDFExportError("report.pdf", "Font not found")
        assert "report.pdf" in exc.message
        assert "Font not found" in exc.details
        assert exc.file_path == "report.pdf"


class TestUtilityFunctions:
    """Tests for utility functions"""
    
    def test_handle_file_not_found_csv(self):
        """Test handle_file_not_found for CSV files"""
        exc = handle_file_not_found("data/transactions.csv")
        assert isinstance(exc, FileNotFoundError)
        assert "Trading212" in exc.details
    
    def test_handle_file_not_found_env(self):
        """Test handle_file_not_found for .env files"""
        exc = handle_file_not_found(".env")
        assert isinstance(exc, FileNotFoundError)
        assert ".env" in exc.details
    
    def test_handle_parsing_error(self):
        """Test handle_parsing_error"""
        original_error = ValueError("invalid literal")
        exc = handle_parsing_error(42, "quantity", "abc", original_error)
        assert isinstance(exc, InvalidTransactionDataError)
        assert exc.row_number == 42
        assert exc.field == "quantity"
        # The details contain the error information
        assert "ValueError" in exc.details


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy"""
    
    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from TaxCalculatorError"""
        exceptions = [
            FileNotFoundError("/path"),
            FileReadError("/path"),
            InvalidCSVFormatError("/path"),
            DateParsingError("date"),
            ExchangeRateError("USD", "2024-01-01"),
            InsufficientSharesError("AAPL", 10, 15),
            ExcelExportError("/path")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, TaxCalculatorError)
            assert isinstance(exc, Exception)
    
    def test_can_catch_by_category(self):
        """Test that exceptions can be caught by their category"""
        from utils.exceptions import FileError, ServiceError, CalculationError
        
        # File errors
        file_exc = FileNotFoundError("/path")
        assert isinstance(file_exc, FileError)
        
        # Service errors
        service_exc = ExchangeRateError("USD", "2024-01-01")
        assert isinstance(service_exc, ServiceError)
        
        # Calculation errors
        calc_exc = InsufficientSharesError("AAPL", 10, 15)
        assert isinstance(calc_exc, CalculationError)
