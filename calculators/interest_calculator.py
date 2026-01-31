from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
import pandas as pd

from models.transaction import Transaction, InterestTransaction
from calculators.calculator_interface import CalculatorInterface


@dataclass
class InterestSummary:
    """Summary of interest by currency"""
    currency: str
    total_interest_foreign: Decimal = Decimal('0')
    total_interest_pln: Decimal = Decimal('0')
    tax_due_poland: Decimal = Decimal('0')
    transactions: List[InterestTransaction] = field(default_factory=list)


@dataclass
class InterestCalculationResult:
    """Result of interest calculation"""
    summaries: Dict[str, InterestSummary] = field(default_factory=dict)
    total_interest_pln: Decimal = Decimal('0')
    total_tax_due: Decimal = Decimal('0')
    stats: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert interest results to a pandas DataFrame"""
        if not self.summaries:
            return pd.DataFrame()
        
        data = []
        for currency, summary in self.summaries.items():
            data.append({
                'currency': currency,
                'total_interest_foreign': float(summary.total_interest_foreign),
                'total_interest_pln': float(summary.total_interest_pln),
                'tax_due_poland': float(summary.tax_due_poland)
            })
        
        return pd.DataFrame(data)


class InterestCalculator(CalculatorInterface[List[Transaction], InterestCalculationResult]):
    """Calculator for interest on cash tax calculation"""
    
    def __init__(self, tax_rate: Decimal = Decimal('0.19')):
        """
        Initialize InterestCalculator.
        
        Args:
            tax_rate: Interest tax rate in Poland (default: 19%)
        """
        self.tax_rate = tax_rate
    
    def validate(self, transactions: List[Transaction]) -> List[str]:
        """
        Validate interest transaction data before calculation.
        
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
        
        # Filter interest transactions
        interest_transactions = [tx for tx in transactions if isinstance(tx, InterestTransaction)]
        
        if not interest_transactions:
            # Not an error - just no interest to process
            return issues
        
        # Check for interest transactions with missing required data
        for i, tx in enumerate(interest_transactions):
            if tx.total_value_pln is None or tx.total_value_pln <= 0:
                issues.append(f"Interest #{i} has no or invalid PLN value: {tx.total_value_pln}")
        
        return issues

    def calculate(self, transactions: List[Transaction], tax_year: Optional[int] = None) -> InterestCalculationResult:
        """
        Calculate interest tax data, optionally filtering by tax year.

        Args:
            transactions: List of transactions to process
            tax_year: Optional tax year to filter interest (only include interest from this year)

        Returns:
            InterestCalculationResult with calculation results
        """
        # Filter interest transactions
        interest_transactions = [tx for tx in transactions if isinstance(tx, InterestTransaction)]

        # Filter by tax year if specified
        if tax_year is not None:
            interest_transactions = [tx for tx in interest_transactions if tx.date.year == tax_year]

        # Validate input data
        issues = self.validate(interest_transactions)
        
        # If no interest transactions, return empty result
        if not interest_transactions:
            return InterestCalculationResult(
                stats={'interest_count': 0, 'tax_year': tax_year},
                issues=issues
            )

        # Statistics
        stats = {
            'interest_count': len(interest_transactions),
            'total_interest_pln': Decimal('0'),
            'total_tax_due': Decimal('0'),
            'tax_year': tax_year
        }

        # Group interest by currency
        summaries = {}
        total_interest_pln = Decimal('0')
        
        for tx in interest_transactions:
            currency = tx.currency or "PLN"
            
            if currency not in summaries:
                summaries[currency] = InterestSummary(currency=currency)
            
            summary = summaries[currency]
            
            # Add interest amount
            if tx.total_value_foreign is not None:
                summary.total_interest_foreign += tx.total_value_foreign
            
            if tx.total_value_pln is not None:
                summary.total_interest_pln += tx.total_value_pln
                total_interest_pln += tx.total_value_pln
                stats['total_interest_pln'] += tx.total_value_pln
            
            # Add transaction to summary
            summary.transactions.append(tx)
        
        # Calculate tax due in Poland for each currency
        total_tax_due = Decimal('0')
        for currency, summary in summaries.items():
            summary.tax_due_poland = summary.total_interest_pln * self.tax_rate
            total_tax_due += summary.tax_due_poland
        
        stats['total_tax_due'] = total_tax_due
        
        # Create result
        result = InterestCalculationResult(
            summaries=summaries,
            total_interest_pln=total_interest_pln,
            total_tax_due=total_tax_due,
            stats=stats,
            issues=issues
        )
        
        return result
