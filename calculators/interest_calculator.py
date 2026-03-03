"""
Interest calculator for cash interest income

Calculates Polish tax on interest received from Trading212 cash accounts.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from decimal import Decimal
import pandas as pd

from models.transaction import Transaction, InterestTransaction
from calculators.calculator_interface import CalculatorInterface


@dataclass
class InterestSummary:
    """Summary of interest for a specific currency"""
    currency: str
    total_interest_foreign: Decimal
    total_interest_pln: Decimal
    tax_due: Decimal


@dataclass
class InterestCalculationResult:
    """Result of interest calculation"""
    summaries: Dict[str, InterestSummary] = field(default_factory=dict)
    total_interest_pln: Decimal = Decimal("0")
    total_tax_due: Decimal = Decimal("0")
    issues: List[str] = field(default_factory=list)


class InterestCalculator(CalculatorInterface[List[Transaction], InterestCalculationResult]):
    """Calculator for interest on cash"""
    
    def __init__(self, tax_rate: Decimal = Decimal("0.19")):
        """
        Initialize InterestCalculator.
        
        Args:
            tax_rate: Tax rate for interest income (default: 19%)
        """
        self.tax_rate = tax_rate
    
    def validate(self, transactions: List[Transaction]) -> List[str]:
        """
        Validate transaction data before calculation.
        
        Args:
            transactions: List of transactions to validate
            
        Returns:
            List of validation issues, empty if no issues
        """
        issues = []
        
        if not transactions:
            return issues
        
        # Filter interest transactions
        interest_txs = [tx for tx in transactions if isinstance(tx, InterestTransaction)]
        
        for tx in interest_txs:
            if tx.exchange_rate is None and tx.currency != 'PLN':
                issues.append(f"Interest transaction on {tx.date} missing exchange rate")
            
            if tx.total_value_pln is None:
                issues.append(f"Interest transaction on {tx.date} missing PLN value")
        
        return issues
    
    def calculate(self, transactions: List[Transaction], tax_year: Optional[int] = None) -> InterestCalculationResult:
        """
        Calculate tax on interest income, optionally filtering by tax year.
        
        Args:
            transactions: List of transactions to process
            tax_year: Optional tax year to filter interest (only include interest from this year)
            
        Returns:
            InterestCalculationResult with calculation results
        """
        # Validate input
        issues = self.validate(transactions)
        
        # Filter interest transactions
        interest_txs = [tx for tx in transactions if isinstance(tx, InterestTransaction)]
        
        # Filter by tax year if specified
        if tax_year:
            interest_txs = [tx for tx in interest_txs if tx.date.year == tax_year]
        
        # Group by currency
        summaries = {}
        total_interest_pln = Decimal("0")
        
        for tx in interest_txs:
            currency = tx.currency
            
            if currency not in summaries:
                summaries[currency] = {
                    'foreign': Decimal("0"),
                    'pln': Decimal("0")
                }
            
            summaries[currency]['foreign'] += tx.total_value_foreign or Decimal("0")
            summaries[currency]['pln'] += tx.total_value_pln or Decimal("0")
            total_interest_pln += tx.total_value_pln or Decimal("0")
        
        # Create summary objects
        summary_objects = {}
        for currency, amounts in summaries.items():
            tax_due = amounts['pln'] * self.tax_rate
            
            summary_objects[currency] = InterestSummary(
                currency=currency,
                total_interest_foreign=amounts['foreign'],
                total_interest_pln=amounts['pln'],
                tax_due=tax_due
            )
        
        # Calculate total tax
        total_tax_due = total_interest_pln * self.tax_rate
        
        return InterestCalculationResult(
            summaries=summary_objects,
            total_interest_pln=total_interest_pln,
            total_tax_due=total_tax_due,
            issues=issues
        )
