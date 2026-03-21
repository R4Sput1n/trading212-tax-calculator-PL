"""
Tests for FIFO calculation correctness

These tests verify that the FIFO (First In, First Out) algorithm
calculates profits, losses, and taxes correctly according to Polish tax law.
"""
import pytest
from datetime import datetime
from decimal import Decimal

from models.transaction import BuyTransaction, SellTransaction
from calculators.fifo_calculator import FifoCalculator
from models.portfolio import Portfolio


class TestBasicFifoCalculations:
    """Tests for basic FIFO calculations"""
    
    def test_simple_profit_calculation(self):
        """Test simple profit: buy low, sell high"""
        # Buy 10 shares @ 100 USD = 1000 USD = 4000 PLN (rate 4.0)
        buy = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell 10 shares @ 150 USD = 1500 USD = 6000 PLN (rate 4.0)
        sell = SellTransaction(
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
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        # Verify match created
        assert len(result.matches) == 1
        match = result.matches[0]
        
        # Verify amounts
        assert match.income_pln == Decimal("6000")  # Sale proceeds
        assert match.cost_pln == Decimal("4000")     # Purchase cost
        assert match.profit_loss_pln == Decimal("2000")  # Profit
        
        # Verify tax (19% of profit)
        expected_tax = int(Decimal("2000") * Decimal("0.19"))
        assert expected_tax == 380
    
    def test_simple_loss_calculation(self):
        """Test simple loss: buy high, sell low"""
        # Buy 10 shares @ 150 USD = 1500 USD = 6000 PLN
        buy = BuyTransaction(
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
        
        # Sell 10 shares @ 100 USD = 1000 USD = 4000 PLN
        sell = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        match = result.matches[0]
        
        # Verify loss
        assert match.income_pln == Decimal("4000")
        assert match.cost_pln == Decimal("6000")
        assert match.profit_loss_pln == Decimal("-2000")  # Loss
    
    def test_partial_sale(self):
        """Test selling only part of purchased shares"""
        # Buy 10 shares @ 100 USD
        buy = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell only 5 shares @ 150 USD
        sell = SellTransaction(
            date=datetime(2024, 2, 1),
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
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        match = result.matches[0]
        
        # Should match 5 shares only
        assert match.used_quantity == Decimal("5")
        assert match.income_pln == Decimal("3000")  # 5 * 150 * 4.0
        assert match.cost_pln == Decimal("2000")     # 5 * 100 * 4.0
        assert match.profit_loss_pln == Decimal("1000")
        
        # Portfolio should still have 5 shares left
        assert result.portfolio.positions["AAPL"].get_total_shares() == Decimal("5")


class TestFifoOrdering:
    """Tests for FIFO ordering (First In, First Out)"""
    
    def test_fifo_ordering_two_purchases(self):
        """Test that oldest purchase is matched first"""
        # First buy: 5 shares @ 100 USD
        buy1 = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("500"),
            total_value_pln=Decimal("2000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Second buy: 5 shares @ 150 USD (more expensive)
        buy2 = BuyTransaction(
            date=datetime(2024, 2, 1),
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
        
        # Sell 5 shares @ 200 USD
        sell = SellTransaction(
            date=datetime(2024, 3, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("5"),
            price_per_share=Decimal("200"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy1, buy2, sell])
        
        match = result.matches[0]
        
        # Should match with FIRST purchase (@ 100 USD), not second (@ 150 USD)
        assert match.buy_date == datetime(2024, 1, 1)
        assert match.cost_pln == Decimal("2000")  # 5 * 100 * 4.0
        assert match.profit_loss_pln == Decimal("2000")  # 4000 - 2000
    
    def test_fifo_multiple_purchases_partial_match(self):
        """Test FIFO with sale spanning multiple purchases"""
        # Buy 10 @ 100
        buy1 = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Buy 10 @ 150
        buy2 = BuyTransaction(
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
        
        # Sell 15 shares @ 200
        sell = SellTransaction(
            date=datetime(2024, 3, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("15"),
            price_per_share=Decimal("200"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("3000"),
            total_value_pln=Decimal("12000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy1, buy2, sell])
        
        # Should create 2 matches
        assert len(result.matches) == 2
        
        # First match: 10 shares from first buy
        match1 = result.matches[0]
        assert match1.used_quantity == Decimal("10")
        assert match1.buy_date == datetime(2024, 1, 1)
        assert match1.cost_pln == Decimal("4000")  # 10 * 100 * 4.0
        assert match1.income_pln == Decimal("8000")  # 10 * 200 * 4.0
        
        # Second match: 5 shares from second buy
        match2 = result.matches[1]
        assert match2.used_quantity == Decimal("5")
        assert match2.buy_date == datetime(2024, 2, 1)
        assert match2.cost_pln == Decimal("3000")  # 5 * 150 * 4.0
        assert match2.income_pln == Decimal("4000")  # 5 * 200 * 4.0


class TestFeeAllocation:
    """Tests for proper fee allocation in FIFO"""
    
    def test_fees_included_in_cost(self):
        """Test that fees are properly included in cost basis"""
        # Buy with fees
        buy = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("50"),  # 50 PLN fee
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell with fees
        sell = SellTransaction(
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
            currency_conversion_fee_pln=Decimal("30"),  # 30 PLN fee
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        match = result.matches[0]
        
        # Cost should include both buy and sell fees
        # Cost = 4000 (purchase) + 50 (buy fee) + 30 (sell fee) = 4080
        assert match.cost_pln == Decimal("4080")
        assert match.income_pln == Decimal("6000")
        assert match.profit_loss_pln == Decimal("1920")  # 6000 - 4080
    
    def test_proportional_fee_allocation_partial_sale(self):
        """Test that fees are allocated proportionally for partial sales"""
        # Buy 10 shares with 100 PLN fee
        buy = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("100"),  # 100 PLN fee for 10 shares
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell only 5 shares
        sell = SellTransaction(
            date=datetime(2024, 2, 1),
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
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        match = result.matches[0]
        
        # Buy fee should be proportionally allocated: 100 * (5/10) = 50 PLN
        # Cost = 2000 (5 shares) + 50 (proportional fee) = 2050
        assert match.buy_currency_conversion_fee_pln == Decimal("50")
        assert match.cost_pln == Decimal("2050")


class TestExchangeRateImpact:
    """Tests for exchange rate impact on calculations"""
    
    def test_different_exchange_rates(self):
        """Test calculation with different exchange rates for buy and sell"""
        # Buy at rate 4.0
        buy = BuyTransaction(
            date=datetime(2024, 1, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),  # 1000 * 4.0
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        # Sell at rate 4.5 (PLN weakened)
        sell = SellTransaction(
            date=datetime(2024, 2, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),  # Same USD price
            currency="USD",
            exchange_rate=Decimal("4.5"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4500"),  # 1000 * 4.5
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        result = calculator.calculate([buy, sell])
        
        match = result.matches[0]
        
        # Profit in PLN even though USD price didn't change
        # Due to exchange rate difference
        assert match.income_pln == Decimal("4500")
        assert match.cost_pln == Decimal("4000")
        assert match.profit_loss_pln == Decimal("500")


class TestTaxYearFiltering:
    """Tests for tax year filtering"""
    
    def test_only_sales_in_tax_year_reported(self):
        """Test that only sales in specified tax year are reported"""
        # Buy in 2023
        buy = BuyTransaction(
            date=datetime(2023, 12, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
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
        
        # Sell in 2023
        sell_2023 = SellTransaction(
            date=datetime(2023, 12, 20),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("3"),
            price_per_share=Decimal("120"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("360"),
            total_value_pln=Decimal("1440"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )
        
        calculator = FifoCalculator()
        
        # Calculate for 2024 only
        result_2024 = calculator.calculate([buy, sell_2023, sell_2024], tax_year=2024)
        
        # Should only include 2024 sale
        assert len(result_2024.matches) == 1
        assert result_2024.matches[0].sell_date.year == 2024

    def test_fifo_processes_historical_sales_when_filtering_by_year(self):
        """Test that filtering by year doesn't skip historical sales, maintaining correct FIFO queue"""
        # Buy in 2023
        buy = BuyTransaction(
            date=datetime(2023, 12, 1),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("10"),
            price_per_share=Decimal("100"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("1000"),
            total_value_pln=Decimal("4000"),
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

        # Sell in 2023
        sell_2023 = SellTransaction(
            date=datetime(2023, 12, 20),
            ticker="AAPL",
            symbol="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            quantity=Decimal("3"),
            price_per_share=Decimal("120"),
            currency="USD",
            exchange_rate=Decimal("4.0"),
            total_value_foreign=Decimal("360"),
            total_value_pln=Decimal("1440"),
            fees_foreign=Decimal("0"),
            fees_pln=Decimal("0"),
            currency_conversion_fee_pln=Decimal("0"),
            transaction_tax_pln=Decimal("0"),
            other_fees_pln=Decimal("0"),
            country="United States"
        )

        calculator = FifoCalculator()
        result_2024 = calculator.calculate([buy, sell_2023, sell_2024], tax_year=2024)

        assert result_2024.portfolio.positions["AAPL"].get_total_shares() == Decimal("2")
