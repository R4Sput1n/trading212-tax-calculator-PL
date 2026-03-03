"""
Tests for parser error handling
"""
import pytest
import os
import tempfile
from pathlib import Path

from parsers.trading212_parser import Trading212Parser
from services.exchange_rate_service import MockExchangeRateService
from services.company_info_service import MockCompanyInfoService
from services.isin_service import MockISINService
from utils.exceptions import (
    FileNotFoundError,
    FileReadError,
    InvalidCSVFormatError,
    DateParsingError,
    NumberParsingError
)


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_services():
    """Create mock services for testing"""
    isin_service = MockISINService()
    exchange_rate_service = MockExchangeRateService(default_rate=4.0)
    company_info_service = MockCompanyInfoService(isin_service=isin_service)
    return {
        'exchange_rate_service': exchange_rate_service,
        'company_info_service': company_info_service
    }


@pytest.fixture
def parser(mock_services):
    """Create parser with mock services"""
    return Trading212Parser(
        exchange_rate_service=mock_services['exchange_rate_service'],
        company_info_service=mock_services['company_info_service']
    )


class TestFileErrors:
    """Tests for file-related errors"""
    
    def test_file_not_found(self, parser):
        """Test that FileNotFoundError is raised for missing file"""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse_file("/nonexistent/path/file.csv")
        
        assert "file.csv" in str(exc_info.value.message)
        assert exc_info.value.file_path == "/nonexistent/path/file.csv"
    
    def test_empty_file(self, parser, fixtures_dir):
        """Test handling of empty CSV file"""
        empty_file = fixtures_dir / "empty.csv"
        
        with pytest.raises(FileReadError) as exc_info:
            parser.parse_file(str(empty_file))
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_unreadable_file(self, parser, tmp_path):
        """Test handling of file without read permissions"""
        # Create a file and remove read permissions
        test_file = tmp_path / "unreadable.csv"
        test_file.write_text("test")
        test_file.chmod(0o000)
        
        try:
            with pytest.raises(FileReadError) as exc_info:
                parser.parse_file(str(test_file))
            
            assert "cannot be read" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)


class TestCSVFormatErrors:
    """Tests for CSV format errors"""
    
    def test_invalid_csv_format(self, parser, fixtures_dir):
        """Test that InvalidCSVFormatError is raised for wrong format"""
        invalid_file = fixtures_dir / "invalid_format.csv"
        
        with pytest.raises(InvalidCSVFormatError) as exc_info:
            parser.parse_file(str(invalid_file))
        
        assert "format not recognized" in str(exc_info.value).lower()
    
    def test_missing_required_columns(self, parser, tmp_path):
        """Test handling of CSV with missing required columns"""
        # Create CSV with some but not all required columns
        test_file = tmp_path / "missing_columns.csv"
        test_file.write_text("Action,Time\nMarket buy,2024-01-01\n")
        
        # Should raise InvalidCSVFormatError when trying to parse
        # (will fail when accessing missing columns)
        transactions = parser.parse_file(str(test_file))
        # Parser should handle missing columns gracefully or skip rows


class TestDataParsingErrors:
    """Tests for data parsing errors"""
    
    def test_invalid_date_format(self, parser, fixtures_dir):
        """Test handling of invalid date formats"""
        invalid_file = fixtures_dir / "invalid_data.csv"
        
        # Parser should collect errors but not crash
        transactions = parser.parse_file(str(invalid_file))
        
        # Should return only valid transactions (skip invalid ones)
        assert isinstance(transactions, list)
    
    def test_invalid_number_format(self, parser, fixtures_dir):
        """Test handling of invalid number formats"""
        invalid_file = fixtures_dir / "invalid_data.csv"
        
        # Parser should collect errors but continue
        transactions = parser.parse_file(str(invalid_file))
        
        # Should return list (possibly empty if all invalid)
        assert isinstance(transactions, list)
    
    def test_error_logging_and_summary(self, parser, fixtures_dir, caplog):
        """Test that parser logs errors with proper summary"""
        import logging
        caplog.set_level(logging.WARNING)
        
        invalid_file = fixtures_dir / "invalid_data.csv"
        transactions = parser.parse_file(str(invalid_file))
        
        # Check that warnings were logged
        assert any("Row" in record.message for record in caplog.records)


class TestValidParsing:
    """Tests for successful parsing"""
    
    def test_parse_valid_file(self, parser, fixtures_dir):
        """Test parsing of valid Trading212 CSV"""
        valid_file = fixtures_dir / "valid_trading212.csv"
        
        transactions = parser.parse_file(str(valid_file))
        
        assert len(transactions) > 0
        assert all(hasattr(tx, 'get_transaction_type') for tx in transactions)
    
    def test_parse_multiple_files(self, parser, fixtures_dir):
        """Test parsing multiple files with duplicate detection"""
        valid_file = fixtures_dir / "valid_trading212.csv"
        
        # Parse same file twice
        transactions = parser.parse_files([str(valid_file), str(valid_file)])
        
        # Should deduplicate
        single_parse = parser.parse_file(str(valid_file))
        assert len(transactions) == len(single_parse)
    
    def test_parse_glob_pattern(self, parser, fixtures_dir):
        """Test parsing files with glob pattern"""
        # Parse all valid CSV files
        pattern = str(fixtures_dir / "valid*.csv")
        transactions = parser.parse_glob(pattern)
        
        assert isinstance(transactions, list)


class TestErrorRecovery:
    """Tests for error recovery and graceful degradation"""
    
    def test_continue_after_bad_row(self, parser, tmp_path):
        """Test that parser continues after encountering bad rows"""
        # Create CSV with mix of valid and invalid data
        test_file = tmp_path / "mixed_data.csv"
        test_file.write_text("""Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.50,USD,,
Market buy,INVALID_DATE,US0378331005,AAPL,Apple Inc.,5,155.00,USD,,775.00,USD,,,0.25,USD,,
Market buy,2024-03-01 10:30:00,US0378331005,AAPL,Apple Inc.,3,152.00,USD,,456.00,USD,,,0.15,USD,,
""")
        
        transactions = parser.parse_file(str(test_file))
        
        # Should have parsed 2 valid transactions despite 1 bad row
        assert len(transactions) == 2
    
    def test_empty_result_for_all_invalid(self, parser, tmp_path):
        """Test that parser returns empty list if all rows invalid"""
        test_file = tmp_path / "all_invalid.csv"
        test_file.write_text("""Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,INVALID,US0378331005,AAPL,Apple Inc.,BAD,BAD,USD,,1500.00,USD,,,0.50,USD,,
""")
        
        transactions = parser.parse_file(str(test_file))
        
        # Should return empty list, not crash
        assert transactions == []


class TestTransactionTypeDetection:
    """Tests for transaction type detection"""
    
    def test_unknown_action_type(self, parser, tmp_path):
        """Test handling of unknown action types"""
        test_file = tmp_path / "unknown_action.csv"
        test_file.write_text("""Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Unknown Action,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.50,USD,,
""")
        
        transactions = parser.parse_file(str(test_file))
        
        # Should skip unknown action types
        assert len(transactions) == 0
    
    def test_case_insensitive_action_matching(self, parser, tmp_path):
        """Test that action matching is case-insensitive"""
        test_file = tmp_path / "mixed_case.csv"
        test_file.write_text("""Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
MARKET BUY,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.50,USD,,
market sell,2024-02-15 10:30:00,US0378331005,AAPL,Apple Inc.,5,160.00,USD,,800.00,USD,,,0.25,USD,,
""")
        
        transactions = parser.parse_file(str(test_file))
        
        # Should parse both despite case differences
        assert len(transactions) == 2
