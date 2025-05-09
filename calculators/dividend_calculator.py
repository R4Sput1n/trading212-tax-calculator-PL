from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
import pandas as pd

from models.transaction import Transaction, DividendTransaction
from calculators.calculator_interface import CalculatorInterface


@dataclass
class DividendSummary:
    """Summary of dividends by country"""
    country: str
    total_dividend_pln: Decimal = Decimal('0')
    tax_paid_abroad_pln: Decimal = Decimal('0')
    tax_due_poland: Decimal = Decimal('0')
    tax_to_pay: Decimal = Decimal('0')
    transactions: List[DividendTransaction] = field(default_factory=list)


@dataclass
class DividendCalculationResult:
    """Result of dividend calculation"""
    summaries: Dict[str, DividendSummary] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert dividend results to a pandas DataFrame"""
        if not self.summaries:
            return pd.DataFrame()
        
        data = []
        for country, summary in self.summaries.items():
            data.append({
                'country': country,
                'total_dividend_pln': float(summary.total_dividend_pln),
                'tax_paid_abroad_pln': float(summary.tax_paid_abroad_pln),
                'tax_due_poland': float(summary.tax_due_poland),
                'tax_to_pay': float(summary.tax_to_pay)
            })
        
        return pd.DataFrame(data)


class DividendCalculator(CalculatorInterface[List[Transaction], DividendCalculationResult]):
    """Calculator for dividend tax calculation"""
    
    def __init__(self, tax_rate: Decimal = Decimal('0.19')):
        """
        Initialize DividendCalculator.
        
        Args:
            tax_rate: Dividend tax rate in Poland (default: 19%)
        """
        self.tax_rate = tax_rate
    
    def validate(self, transactions: List[Transaction]) -> List[str]:
        """
        Validate dividend transaction data before calculation.
        
        Args:
            transactions: List of transactions to validate
            
        Returns:
            List of validation issues, empty if no issues
        """
        issues = []
        
        # Check if there are any transactions
        if not transactions:
            issues.append("No transactions to process")
            return issues
        
        # Filter dividend transactions
        dividend_transactions = [tx for tx in transactions if isinstance(tx, DividendTransaction)]
        
        if not dividend_transactions:
            issues.append("No dividend transactions found")
            return issues
        
        # Check for dividend transactions with missing required data
        for i, tx in enumerate(dividend_transactions):
            if tx.ticker == '':
                issues.append(f"Dividend #{i} has no ticker")
            
            if tx.quantity <= 0:
                issues.append(f"Dividend #{i} has invalid quantity: {tx.quantity}")
            
            if tx.exchange_rate is None and tx.currency != 'PLN':
                issues.append(f"Dividend #{i} has no exchange rate for currency: {tx.currency}")
            
            if tx.total_value_pln is None:
                issues.append(f"Dividend #{i} has no PLN value")
            
            if tx.country is None or tx.country == "":
                issues.append(f"Dividend #{i} has no country information")
        
        return issues

    def calculate(self, transactions: List[Transaction], tax_year: Optional[int] = None) -> DividendCalculationResult:
        """
        Calculate dividend tax data, optionally filtering by tax year.

        Args:
            transactions: List of transactions to process
            tax_year: Optional tax year to filter dividends (only include dividends from this year)

        Returns:
            DividendCalculationResult with calculation results
        """
        # Filter dividend transactions
        dividend_transactions = [tx for tx in transactions if isinstance(tx, DividendTransaction)]

        # Filter by tax year if specified
        if tax_year is not None:
            dividend_transactions = [tx for tx in dividend_transactions if tx.date.year == tax_year]

        # Validate input data
        issues = self.validate(dividend_transactions)
        if issues and "No dividend transactions found" in issues:
            # If only issue is no dividends, return empty result without issues
            issues = []
            return DividendCalculationResult(issues=issues)
        elif issues:
            return DividendCalculationResult(issues=issues)

        # Statistics
        stats = {
            'dividend_count': len(dividend_transactions),
            'total_dividend_pln': Decimal('0'),
            'total_tax_paid_abroad_pln': Decimal('0'),
            'total_tax_due_poland': Decimal('0'),
            'total_tax_to_pay': Decimal('0'),
            'tax_year': tax_year
        }

        # Group dividends by country
        summaries = {}
        
        for tx in dividend_transactions:
            country = tx.country or "Unknown"
            
            if country not in summaries:
                summaries[country] = DividendSummary(country=country)
            
            summary = summaries[country]
            
            # Add dividend amount
            if tx.total_value_pln is not None:
                summary.total_dividend_pln += tx.total_value_pln
                stats['total_dividend_pln'] += tx.total_value_pln
            
            # Add tax paid abroad
            if tx.withholding_tax_pln is not None:
                summary.tax_paid_abroad_pln += tx.withholding_tax_pln
                stats['total_tax_paid_abroad_pln'] += tx.withholding_tax_pln
            
            # Add transaction to summary
            summary.transactions.append(tx)
        
        # Calculate tax due in Poland and tax to pay
        for country, summary in summaries.items():
            # Tax due in Poland (19% of dividend)
            summary.tax_due_poland = summary.total_dividend_pln * self.tax_rate
            stats['total_tax_due_poland'] += summary.tax_due_poland
            
            # Tax to pay (difference, not less than 0)
            summary.tax_to_pay = max(Decimal('0'), summary.tax_due_poland - summary.tax_paid_abroad_pln)
            stats['total_tax_to_pay'] += summary.tax_to_pay
        
        # Create result
        result = DividendCalculationResult(
            summaries=summaries,
            stats=stats,
            issues=issues
        )
        
        return result
