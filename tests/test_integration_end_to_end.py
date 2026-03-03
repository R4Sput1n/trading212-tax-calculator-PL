"""
Integration tests using real CSV files

These tests verify the entire pipeline from CSV input to final tax calculations,
testing all components working together as they would in production.
"""
import pytest
import tempfile
import os
from pathlib import Path
from decimal import Decimal

from parsers.trading212_parser import Trading212Parser
from services.exchange_rate_service import MockExchangeRateService
from services.company_info_service import MockCompanyInfoService
from services.isin_service import MockISINService
from calculators.fifo_calculator import FifoCalculator
from calculators.dividend_calculator import DividendCalculator
from exporters.tax_form_exporter import TaxFormGenerator


class TestEndToEndIntegration:
    """End-to-end integration tests using CSV files"""
    
    @pytest.fixture
    def setup_services(self):
        """Setup mock services with predictable values"""
        isin_service = MockISINService()
        exchange_rate_service = MockExchangeRateService(default_rate=4.0)
        company_info_service = MockCompanyInfoService(isin_service=isin_service)
        
        return {
            'exchange_rate_service': exchange_rate_service,
            'company_info_service': company_info_service
        }
    
    def test_simple_buy_and_sell_scenario(self, setup_services, tmp_path):
        """
        Test complete flow: CSV -> Parse -> Calculate -> Tax Forms
        
        Scenario:
        - Buy 10 AAPL @ $100 = $1000 = 4000 PLN
        - Sell 10 AAPL @ $150 = $1500 = 6000 PLN
        Expected profit: 2000 PLN
        Expected tax: 380 PLN
        """
        # Create CSV file
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,100.00,USD,,1000.00,USD,,,0.00,USD,,
Market sell,2024-02-15 11:45:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.00,USD,,"""
        
        csv_file = tmp_path / "test_transactions.csv"
        csv_file.write_text(csv_content)
        
        # Parse CSV
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        # Verify parsing
        assert len(transactions) == 2
        assert transactions[0].get_transaction_type() == "BUY"
        assert transactions[1].get_transaction_type() == "SELL"
        
        # Calculate FIFO
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        # Verify FIFO calculation
        assert len(fifo_result.matches) == 1
        match = fifo_result.matches[0]
        
        assert match.income_pln == Decimal("6000")
        assert match.cost_pln == Decimal("4000")
        assert match.profit_loss_pln == Decimal("2000")
        
        # Generate tax forms
        dividend_calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        dividend_result = dividend_calculator.calculate(transactions)
        
        tax_form_generator = TaxFormGenerator(tax_rate=0.19)
        tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result)
        
        # Verify tax form data
        assert tax_form_data.pit38.total_income == Decimal("6000")
        assert tax_form_data.pit38.total_cost == Decimal("4000")
        assert tax_form_data.pit38.profit == Decimal("2000")
        assert tax_form_data.pit38.tax_base == 2000
        assert tax_form_data.pit38.tax_due == 380  # 2000 * 0.19
    
    def test_buy_sell_with_dividends(self, setup_services, tmp_path):
        """
        Test scenario with both stock sales and dividends
        
        Scenario:
        - Buy 100 AAPL
        - Receive dividend with 15% withholding
        - Sell 50 AAPL
        """
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,100,100.00,USD,,10000.00,USD,,,0.00,USD,,
Dividend (Ordinary),2024-02-15 09:00:00,US0378331005,AAPL,Apple Inc.,100,1.00,USD,,100.00,USD,15.00,USD,,,
Market sell,2024-03-15 11:45:00,US0378331005,AAPL,Apple Inc.,50,150.00,USD,,7500.00,USD,,,0.00,USD,,"""
        
        csv_file = tmp_path / "test_with_dividend.csv"
        csv_file.write_text(csv_content)
        
        # Parse
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        assert len(transactions) == 3
        
        # Calculate
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        dividend_calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        dividend_result = dividend_calculator.calculate(transactions)
        
        # Verify FIFO (50 shares sold)
        assert len(fifo_result.matches) == 1
        assert fifo_result.matches[0].used_quantity == Decimal("50")
        assert fifo_result.matches[0].income_pln == Decimal("30000")  # 50 * 150 * 4.0
        assert fifo_result.matches[0].cost_pln == Decimal("20000")    # 50 * 100 * 4.0
        assert fifo_result.matches[0].profit_loss_pln == Decimal("10000")
        
        # Verify dividend
        assert "United States" in dividend_result.summaries
        us_div = dividend_result.summaries["United States"]
        assert us_div.total_dividend_pln == Decimal("400")  # 100 * 4.0
        assert us_div.tax_paid_abroad_pln == Decimal("60")  # 15 * 4.0
        assert us_div.tax_due_poland == Decimal("76")       # 400 * 0.19
        assert us_div.tax_to_pay == Decimal("16")           # 76 - 60
        
        # Generate tax form
        tax_form_generator = TaxFormGenerator(tax_rate=0.19)
        tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result)
        
        # Verify combined tax form
        assert tax_form_data.pit38.profit == Decimal("10000")
        assert tax_form_data.pit38.tax_due == 1900  # 10000 * 0.19
        assert len(tax_form_data.pit38.dividend_data) == 1
        assert tax_form_data.pit38.dividend_data[0]["dividend_amount"] == Decimal("400")
    
    def test_multiple_stocks_different_countries(self, setup_services, tmp_path):
        """
        Test scenario with stocks from different countries
        
        Verifies that PIT/ZG forms are properly separated by country
        """
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,100.00,USD,,1000.00,USD,,,0.00,USD,,
Market buy,2024-01-16 10:30:00,GB0031348658,BARC,Barclays PLC,20,50.00,GBP,,1000.00,GBP,,,0.00,GBP,,
Market sell,2024-02-15 11:45:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.00,USD,,
Market sell,2024-02-16 11:45:00,GB0031348658,BARC,Barclays PLC,20,60.00,GBP,,1200.00,GBP,,,0.00,GBP,,"""
        
        csv_file = tmp_path / "test_multi_country.csv"
        csv_file.write_text(csv_content)
        
        # Parse
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        # Calculate
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        dividend_calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        dividend_result = dividend_calculator.calculate(transactions)
        
        # Generate tax forms
        tax_form_generator = TaxFormGenerator(tax_rate=0.19)
        tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result)
        
        # Verify PIT/ZG has entries for both countries
        assert len(tax_form_data.pitzg) == 2
        
        countries = {entry.country for entry in tax_form_data.pitzg}
        assert "United States" in countries
        assert "United Kingdom" in countries
        
        # Find US and UK entries
        us_entry = next(e for e in tax_form_data.pitzg if e.country == "United States")
        uk_entry = next(e for e in tax_form_data.pitzg if e.country == "United Kingdom")
        
        # Verify US calculations
        # Buy: 10 @ 100 USD = 4000 PLN, Sell: 10 @ 150 USD = 6000 PLN
        assert us_entry.securities_income == Decimal("6000")
        assert us_entry.securities_cost == Decimal("4000")
        assert us_entry.securities_profit == Decimal("2000")
        
        # Verify UK calculations (assuming rate 5.0 for GBP from MockExchangeRateService)
        # Buy: 20 @ 50 GBP = 5000 PLN, Sell: 20 @ 60 GBP = 6000 PLN
        assert uk_entry.securities_income == Decimal("6000")  # 20 * 60 * 5.0
        assert uk_entry.securities_cost == Decimal("5000")    # 20 * 50 * 5.0
        assert uk_entry.securities_profit == Decimal("1000")
    
    def test_fifo_spanning_multiple_purchases(self, setup_services, tmp_path):
        """
        Test FIFO calculation when sale spans multiple purchases
        
        Scenario:
        - Buy 10 @ $100
        - Buy 10 @ $120
        - Sell 15 @ $150
        
        Should match: 10 from first buy + 5 from second buy
        """
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,100.00,USD,,1000.00,USD,,,0.00,USD,,
Market buy,2024-02-01 10:30:00,US0378331005,AAPL,Apple Inc.,10,120.00,USD,,1200.00,USD,,,0.00,USD,,
Market sell,2024-03-15 11:45:00,US0378331005,AAPL,Apple Inc.,15,150.00,USD,,2250.00,USD,,,0.00,USD,,"""
        
        csv_file = tmp_path / "test_multi_purchase.csv"
        csv_file.write_text(csv_content)
        
        # Parse and calculate
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        # Should have 2 matches
        assert len(fifo_result.matches) == 2
        
        # First match: 10 shares from first purchase @ $100
        match1 = fifo_result.matches[0]
        assert match1.used_quantity == Decimal("10")
        assert match1.cost_pln == Decimal("4000")   # 10 * 100 * 4.0
        assert match1.income_pln == Decimal("6000")  # 10 * 150 * 4.0
        assert match1.profit_loss_pln == Decimal("2000")
        
        # Second match: 5 shares from second purchase @ $120
        match2 = fifo_result.matches[1]
        assert match2.used_quantity == Decimal("5")
        assert match2.cost_pln == Decimal("2400")   # 5 * 120 * 4.0
        assert match2.income_pln == Decimal("3000")  # 5 * 150 * 4.0
        assert match2.profit_loss_pln == Decimal("600")
        
        # Total profit: 2000 + 600 = 2600 PLN
        total_profit = sum(m.profit_loss_pln for m in fifo_result.matches)
        assert total_profit == Decimal("2600")
        
        # Remaining shares: 20 - 15 = 5 shares
        assert fifo_result.portfolio.positions["AAPL"].get_total_shares() == Decimal("5")
    
    def test_with_transaction_fees(self, setup_services, tmp_path):
        """
        Test that transaction fees are properly included in calculations
        
        Fees should increase cost basis and reduce profit
        """
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,100.00,USD,,1000.00,USD,,,2.50,USD,,
Market sell,2024-02-15 11:45:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,3.00,USD,,"""
        
        csv_file = tmp_path / "test_with_fees.csv"
        csv_file.write_text(csv_content)
        
        # Parse and calculate
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        match = fifo_result.matches[0]
        
        # Income: 10 * 150 * 4.0 = 6000 PLN
        assert match.income_pln == Decimal("6000")
        
        # Cost: (10 * 100 * 4.0) + (2.50 * 4.0) + (3.00 * 4.0)
        #     = 4000 + 10 + 12 = 4022 PLN
        assert match.cost_pln == Decimal("4022")
        
        # Profit: 6000 - 4022 = 1978 PLN
        assert match.profit_loss_pln == Decimal("1978")
        
        # Verify fees are broken down correctly
        assert match.buy_currency_conversion_fee_pln == Decimal("10")  # 2.50 * 4.0
        assert match.sell_currency_conversion_fee_pln == Decimal("12")  # 3.00 * 4.0
    
    def test_tax_year_filtering_from_csv(self, setup_services, tmp_path):
        """
        Test that tax year filtering works correctly with CSV input
        
        Only sales in specified year should be reported
        """
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2023-12-15 10:30:00,US0378331005,AAPL,Apple Inc.,20,100.00,USD,,2000.00,USD,,,0.00,USD,,
Market sell,2023-12-20 11:45:00,US0378331005,AAPL,Apple Inc.,5,120.00,USD,,600.00,USD,,,0.00,USD,,
Market sell,2024-01-15 11:45:00,US0378331005,AAPL,Apple Inc.,10,150.00,USD,,1500.00,USD,,,0.00,USD,,
Dividend (Ordinary),2023-12-10 09:00:00,US0378331005,AAPL,Apple Inc.,20,1.00,USD,,20.00,USD,3.00,USD,,,
Dividend (Ordinary),2024-02-10 09:00:00,US0378331005,AAPL,Apple Inc.,20,1.00,USD,,20.00,USD,3.00,USD,,,"""
        
        csv_file = tmp_path / "test_year_filter.csv"
        csv_file.write_text(csv_content)
        
        # Parse
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        # Calculate for 2024 only
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions, tax_year=2024)
        
        dividend_calculator = DividendCalculator(tax_rate=Decimal("0.19"))
        dividend_result = dividend_calculator.calculate(transactions, tax_year=2024)
        
        # Should only have 2024 sale
        assert len(fifo_result.matches) == 1
        assert fifo_result.matches[0].sell_date.year == 2024
        
        # Should only have 2024 dividend
        us_div = dividend_result.summaries["United States"]
        assert us_div.total_dividend_pln == Decimal("80")  # Only one dividend of $20 * 4.0
        
        # Generate tax forms for 2024
        tax_form_generator = TaxFormGenerator(tax_rate=0.19)
        tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result)
        
        # Verify only 2024 data included
        # Sale: 10 @ 150 - cost depends on FIFO order
        assert tax_form_data.pit38.total_income == Decimal("6000")  # 10 * 150 * 4.0


class TestEdgeCasesIntegration:
    """Integration tests for edge cases"""
    
    @pytest.fixture
    def setup_services(self):
        """Setup mock services"""
        isin_service = MockISINService()
        exchange_rate_service = MockExchangeRateService(default_rate=4.0)
        company_info_service = MockCompanyInfoService(isin_service=isin_service)
        
        return {
            'exchange_rate_service': exchange_rate_service,
            'company_info_service': company_info_service
        }
    
    def test_empty_csv_file(self, setup_services, tmp_path):
        """Test handling of empty CSV file"""
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)"""
        
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text(csv_content)
        
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        # Should return empty list, not crash
        assert transactions == []
    
    def test_only_buys_no_sales(self, setup_services, tmp_path):
        """Test scenario with only purchases, no sales"""
        csv_content = """Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Total,Currency (Total),Withholding tax,Currency (Withholding tax),Currency conversion fee,Currency (Currency conversion fee),French transaction tax,Currency (French transaction tax)
Market buy,2024-01-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,100.00,USD,,1000.00,USD,,,0.00,USD,,
Market buy,2024-02-15 10:30:00,US0378331005,AAPL,Apple Inc.,10,120.00,USD,,1200.00,USD,,,0.00,USD,,"""
        
        csv_file = tmp_path / "only_buys.csv"
        csv_file.write_text(csv_content)
        
        parser = Trading212Parser(
            exchange_rate_service=setup_services['exchange_rate_service'],
            company_info_service=setup_services['company_info_service']
        )
        transactions = parser.parse_file(str(csv_file))
        
        fifo_calculator = FifoCalculator()
        fifo_result = fifo_calculator.calculate(transactions)
        
        # No sales, so no matches
        assert len(fifo_result.matches) == 0
        
        # But portfolio should have shares
        assert fifo_result.portfolio.positions["AAPL"].get_total_shares() == Decimal("20")
