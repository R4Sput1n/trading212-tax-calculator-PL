"""
Tests for calculator error handling
"""
import pytest
from datetime import datetime
from decimal import Decimal

from models.transaction import BuyTransaction, SellTransaction, DividendTransaction
from models.portfolio import Portfolio, PortfolioPosition
from calculators.fifo_calculator import FifoCalculator
from calculators.dividend_calculator import DividendCalculator
from utils.exceptions import InsufficientSharesError, FIFOCalculationError

# Note: InterestCalculator tests removed as the module doesn't exist yet


class TestPortfolioErrors:
    """Tests for Portfolio error handling"""
    
    def test_sell_without_purchase_raises_error(self):
        """Test that selling without prior purchase raises InsufficientSharesError"""
        portfolio = Portfolio()
        
        sell_tx = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        with pytest.raises(InsufficientSharesError) as exc_info:
            portfolio.process_sale(sell_tx)
        
        assert exc_info.value.ticker == "AAPL"
        assert exc_info.value.available == 0
        assert exc_info.value.requested == 10.0
    
    def test_sell_more_than_available_raises_error(self):
        """Test that selling more than available raises InsufficientSharesError"""
        portfolio = Portfolio()
        
        # Buy 5 shares
        buy_tx = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("750"),
            total_value_pln=Decimal("3000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        portfolio.add_transaction(buy_tx)
        
        # Try to sell 10 shares
        sell_tx = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("160"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1600"),
            total_value_pln=Decimal("6400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        with pytest.raises(InsufficientSharesError) as exc_info:
            portfolio.process_sale(sell_tx)
        
        assert exc_info.value.ticker == "AAPL"
        assert exc_info.value.available == 5.0
        assert exc_info.value.requested == 10.0
    
    def test_successful_sale_with_sufficient_shares(self):
        """Test that sale succeeds with sufficient shares"""
        portfolio = Portfolio()
        
        # Buy 10 shares
        buy_tx = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        portfolio.add_transaction(buy_tx)
        
        # Sell 5 shares
        sell_tx = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("160"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("800"),
            total_value_pln=Decimal("3200"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        matches = portfolio.process_sale(sell_tx)
        
        assert len(matches) == 1
        assert matches[0].used_quantity == Decimal("5")


class TestFifoCalculatorErrors:
    """Tests for FIFO calculator error handling"""
    
    def test_empty_transactions_list(self):
        """Test handling of empty transactions list"""
        calculator = FifoCalculator()
        
        result = calculator.calculate([])
        
        assert len(result.matches) == 0
        assert "No transactions" in result.issues[0]
    
    def test_validation_catches_missing_exchange_rate(self):
        """Test that validation catches missing exchange rate"""
        calculator = FifoCalculator()
        
        # Create transaction with no exchange rate
        tx = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=None,  # Missing!
            total_value_foreign=Decimal("1500"),
            total_value_pln=None,
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        issues = calculator.validate([tx])
        
        assert len(issues) > 0
        assert any("exchange rate" in issue.lower() for issue in issues)
    
    def test_insufficient_shares_error_recorded_as_issue(self):
        """Test that InsufficientSharesError is recorded as issue"""
        calculator = FifoCalculator()
        
        # Only sell, no buy
        sell_tx = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("160"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1600"),
            total_value_pln=Decimal("6400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        result = calculator.calculate([sell_tx])
        
        # Should have recorded error as issue
        assert len(result.issues) > 0
        assert any("AAPL" in issue for issue in result.issues)
    
    def test_year_filtering_works(self):
        """Test that tax year filtering works correctly"""
        calculator = FifoCalculator()
        
        # Buy in 2023
        buy_tx = BuyTransaction(
            date=datetime(2023, 12, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell in 2023
        sell_2023 = SellTransaction(
            date=datetime(2023, 12, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("160"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("800"),
            total_value_pln=Decimal("3200"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell in 2024
        sell_2024 = SellTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("3"),
            price_per_share=Decimal("165"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("495"),
            total_value_pln=Decimal("1980"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Calculate for 2024 only
        result = calculator.calculate([buy_tx, sell_2023, sell_2024], tax_year=2024)
        
        # Should only have 1 match (2024 sale)
        assert len(result.matches) == 1
        assert result.matches[0].sell_date.year == 2024


class TestDividendCalculatorErrors:
    """Tests for dividend calculator error handling"""
    
    def test_empty_transactions_list(self):
        """Test handling of empty transactions list"""
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        
        result = calculator.calculate([])
        
        assert len(result.summaries) == 0
    
    def test_no_dividend_transactions(self):
        """Test handling when no dividend transactions"""
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        
        # Only buy transaction
        buy_tx = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        result = calculator.calculate([buy_tx])
        
        assert len(result.summaries) == 0


# InterestCalculator tests skipped - module doesn't exist yet


class TestCalculatorRecovery:
    """Tests for calculator error recovery"""
    
    def test_continues_processing_after_error(self):
        """Test that calculator continues processing after encountering an error"""
        calculator = FifoCalculator()
        
        # Buy AAPL
        buy_aapl = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("150"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell MSFT (without buying - will error)
        sell_msft = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="MSFT",
            symbol="MSFT",
            isin="US5949181045",
            name="Microsoft Corp.",
            quantity=Decimal("5"),
            price_per_share=Decimal("300"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1500"),
            total_value_pln=Decimal("6000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell AAPL (should succeed)
        sell_aapl = SellTransaction(
            date=datetime(2024, 3, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("160"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("800"),
            total_value_pln=Decimal("3200"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        result = calculator.calculate([buy_aapl, sell_msft, sell_aapl])
        
        # Should have 1 successful match (AAPL)
        assert len(result.matches) == 1
        
        # Should have 1 error (MSFT)
        assert len(result.issues) == 1
        assert "MSFT" in result.issues[0]
