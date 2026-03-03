"""
Tests for dividend calculation correctness

These tests verify that dividend calculations, including foreign tax credits
and Polish tax calculations, are correct according to Polish tax law.
"""
import pytest
from datetime import datetime
from decimal import Decimal

from models.transaction import DividendTransaction
from calculators.dividend_calculator import DividendCalculator


class TestBasicDividendCalculations:
    """Tests for basic dividend calculations"""
    
    def test_us_dividend_with_15_percent_withholding(self):
        """
        Test US dividend with 15% withholding tax (W-8BEN).
        
        Polish tax: 19%
        Foreign withholding: 15%
        Tax to pay in Poland: 19% - 15% = 4%
        """
        # Gross dividend: $100
        # Withholding tax (15%): $15
        # Net received: $85
        # At rate 4.0: 400 PLN gross, 60 PLN withheld
        dividend = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("100"),  # Number of shares
            price_per_share=Decimal("1.00"),  # $1 per share
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),  # Gross dividend
            total_value_pln=Decimal("400"),  # 100 * 4.0
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),  # $15 withheld
            withholding_tax_pln=Decimal("60")  # 15 * 4.0
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([dividend])
        
        # Check summary for United States
        assert "United States" in result.summaries
        us_summary = result.summaries["United States"]
        
        # Verify calculations
        assert us_summary.total_dividend_pln == Decimal("400")
        assert us_summary.tax_paid_abroad_pln == Decimal("60")
        
        # Polish tax due: 400 * 0.19 = 76 PLN
        assert us_summary.tax_due_poland == Decimal("76")
        
        # Tax to pay in Poland: 76 - 60 = 16 PLN
        assert us_summary.tax_to_pay == Decimal("16")
    
    def test_uk_dividend_no_withholding(self):
        """
        Test UK dividend with 0% withholding tax.
        
        UK doesn't withhold tax on dividends, so full 19% due in Poland.
        """
        # Gross dividend: £100
        # No withholding
        # At rate 5.0: 500 PLN
        dividend = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="BP",
            symbol="BP",
            isin="GB0007980591",
            name="BP plc",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="GBP",
            exchange_rate=Decimal("5.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("500"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United Kingdom",
            withholding_tax_foreign=Decimal("0"),  # No withholding
            withholding_tax_pln=Decimal("0")
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([dividend])
        
        uk_summary = result.summaries["United Kingdom"]
        
        assert uk_summary.total_dividend_pln == Decimal("500")
        assert uk_summary.tax_paid_abroad_pln == Decimal("0")
        assert uk_summary.tax_due_poland == Decimal("95")  # 500 * 0.19
        assert uk_summary.tax_to_pay == Decimal("95")  # Full Polish tax
    
    def test_multiple_dividends_same_country(self):
        """Test aggregation of multiple dividends from same country"""
        # First dividend
        div1 = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),
            withholding_tax_pln=Decimal("60")
        )
        
        # Second dividend from different US company
        div2 = DividendTransaction(
            date=datetime(2024, 2, 15),
            ticker="MSFT",
            symbol="MSFT",
            isin="US5949181045",
            name="Microsoft Corp.",
            quantity=Decimal("50"),
            price_per_share=Decimal("2.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),
            withholding_tax_pln=Decimal("60")
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([div1, div2])
        
        # Should aggregate both under United States
        assert len(result.summaries) == 1
        us_summary = result.summaries["United States"]
        
        # Total: 400 + 400 = 800 PLN
        assert us_summary.total_dividend_pln == Decimal("800")
        
        # Total withholding: 60 + 60 = 120 PLN
        assert us_summary.tax_paid_abroad_pln == Decimal("120")
        
        # Polish tax: 800 * 0.19 = 152 PLN
        assert us_summary.tax_due_poland == Decimal("152")
        
        # To pay: 152 - 120 = 32 PLN
        assert us_summary.tax_to_pay == Decimal("32")
    
    def test_dividends_from_multiple_countries(self):
        """Test dividends from different countries are separated"""
        # US dividend
        us_div = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),
            withholding_tax_pln=Decimal("60")
        )
        
        # UK dividend
        uk_div = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="BP",
            symbol="BP",
            isin="GB0007980591",
            name="BP plc",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="GBP",
            exchange_rate=Decimal("5.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("500"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United Kingdom",
            withholding_tax_foreign=Decimal("0"),
            withholding_tax_pln=Decimal("0")
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([us_div, uk_div])
        
        # Should have separate entries for each country
        assert len(result.summaries) == 2
        assert "United States" in result.summaries
        assert "United Kingdom" in result.summaries


class TestTaxCreditCalculations:
    """Tests for foreign tax credit calculations"""
    
    def test_tax_credit_cannot_exceed_polish_tax(self):
        """Test that foreign tax credit cannot exceed Polish tax due"""
        # Edge case: Foreign withholding > Polish tax
        # If foreign country withholds more than 19%, excess is not refunded
        dividend = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="XYZ",
            symbol="XYZ",
            isin="XX1234567890",
            name="High Tax Country Corp.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="High Tax Country",
            withholding_tax_foreign=Decimal("30"),  # 30% withheld
            withholding_tax_pln=Decimal("120")  # 30 * 4.0
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([dividend])
        
        summary = result.summaries["High Tax Country"]
        
        # Polish tax due: 400 * 0.19 = 76 PLN
        assert summary.tax_due_poland == Decimal("76")
        
        # But foreign tax paid was 120 PLN
        assert summary.tax_paid_abroad_pln == Decimal("120")
        
        # Tax to pay should be 0 (not negative)
        # You don't get refund for excess foreign tax
        assert summary.tax_to_pay == Decimal("0")
    
    def test_zero_withholding_means_full_polish_tax(self):
        """Test that 0% withholding means full 19% due in Poland"""
        dividend = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="TEST",
            symbol="TEST",
            isin="XX1234567890",
            name="Test Corp.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="Test Country",
            withholding_tax_foreign=None,  # No withholding
            withholding_tax_pln=None
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([dividend])
        
        summary = result.summaries["Test Country"]
        
        assert summary.tax_due_poland == Decimal("76")  # 400 * 0.19
        assert summary.tax_paid_abroad_pln == Decimal("0")
        assert summary.tax_to_pay == Decimal("76")


class TestTaxYearFiltering:
    """Tests for tax year filtering in dividend calculations"""
    
    def test_only_dividends_in_tax_year_reported(self):
        """Test that only dividends in specified tax year are reported"""
        # 2023 dividend
        div_2023 = DividendTransaction(
            date=datetime(2023, 12, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),
            withholding_tax_pln=Decimal("60")
        )
        
        # 2024 dividend
        div_2024 = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("100"),
            price_per_share=Decimal("1.00"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("100"),
            total_value_pln=Decimal("400"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("15"),
            withholding_tax_pln=Decimal("60")
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        
        # Calculate for 2024 only
        result = calculator.calculate([div_2023, div_2024], tax_year=2024)
        
        us_summary = result.summaries["United States"]
        
        # Should only include 2024 dividend
        assert us_summary.total_dividend_pln == Decimal("400")  # Only one dividend
        assert us_summary.tax_paid_abroad_pln == Decimal("60")


class TestEdgeCases:
    """Tests for edge cases in dividend calculations"""
    
    def test_very_small_dividend(self):
        """Test calculation with very small dividend amount"""
        dividend = DividendTransaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("1"),
            price_per_share=Decimal("0.01"),  # 1 cent
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("0.01"),
            total_value_pln=Decimal("0.04"),  # 0.01 * 4.0
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States",
            withholding_tax_foreign=Decimal("0.0015"),  # 15% of 0.01
            withholding_tax_pln=Decimal("0.006")  # 0.0015 * 4.0
        )
        
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([dividend])
        
        # Should handle without errors
        assert "United States" in result.summaries
        us_summary = result.summaries["United States"]
        
        # Verify precision maintained
        assert us_summary.total_dividend_pln == Decimal("0.04")
    
    def test_empty_dividend_list(self):
        """Test calculation with no dividends"""
        calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        result = calculator.calculate([])
        
        # Should return empty result without errors
        assert len(result.summaries) == 0
