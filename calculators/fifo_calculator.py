from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd

from models.transaction import Transaction, BuyTransaction, SellTransaction, FifoMatchResult
from models.portfolio import Portfolio
from calculators.calculator_interface import CalculatorInterface


@dataclass
class FifoCalculationResult:
    """Result of FIFO calculation"""
    matches: List[FifoMatchResult] = field(default_factory=list)
    portfolio: Portfolio = field(default_factory=Portfolio)
    stats: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert FIFO results to a pandas DataFrame"""
        if not self.matches:
            return pd.DataFrame()
        
        data = []
        for match in self.matches:
            data.append({
                'ticker': match.ticker,
                'buy_date': match.buy_date,
                'sell_date': match.sell_date,
                'shares': match.used_quantity,
                'income_pln': match.income_pln,
                'cost_pln': match.cost_pln,
                'profit_loss_pln': match.profit_loss_pln,
                'country': match.country
            })
        
        return pd.DataFrame(data)


class FifoCalculator(CalculatorInterface[List[Transaction], FifoCalculationResult]):
    """Calculator for FIFO method tax calculation"""
    
    def validate(self, transactions: List[Transaction]) -> List[str]:
        """
        Validate transaction data before FIFO calculation.
        
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
        
        # Check for transactions with missing required data
        for i, tx in enumerate(transactions):
            if not hasattr(tx, 'get_transaction_type'):
                issues.append(f"Transaction #{i} is not a valid Transaction object")
                continue
                
            if tx.ticker == '':
                issues.append(f"Transaction #{i} ({tx.get_transaction_type()}) has no ticker")
            
            if tx.quantity <= 0:
                issues.append(f"Transaction #{i} ({tx.get_transaction_type()}) has invalid quantity: {tx.quantity}")
            
            if tx.exchange_rate is None and tx.currency != 'PLN':
                issues.append(f"Transaction #{i} ({tx.get_transaction_type()}) has no exchange rate for currency: {tx.currency}")
            
            if tx.total_value_pln is None:
                issues.append(f"Transaction #{i} ({tx.get_transaction_type()}) has no PLN value")
        
        return issues

    def calculate(self, transactions: List[Transaction], tax_year: Optional[int] = None) -> FifoCalculationResult:
        """
        Calculate tax data using FIFO method, optionally filtering sales by tax year.

        Args:
            transactions: List of transactions to process
            tax_year: Optional tax year to filter sales (only include sales from this year)

        Returns:
            FifoCalculationResult with calculation results
        """
        # Validate input data
        issues = self.validate(transactions)
        if issues:
            return FifoCalculationResult(issues=issues)

        # Statistics
        stats = {
            'buy_count': 0,
            'sell_count': 0,
            'fifo_match_count': 0,
            'tax_year': tax_year
        }

        # Create portfolio and process transactions in chronological order
        portfolio = Portfolio()
        matches = []

        # Sort transactions by date
        sorted_transactions = sorted(transactions, key=lambda tx: tx.date)

        # Process transactions
        for tx in sorted_transactions:
            if isinstance(tx, BuyTransaction):
                portfolio.add_transaction(tx)
                stats['buy_count'] += 1

            elif isinstance(tx, SellTransaction):
                # Skip this sale if it's not in the specified tax year
                if tax_year is not None and tx.date.year != tax_year:
                    continue

                try:
                    # Process sale using FIFO
                    sale_matches = portfolio.process_sale(tx)
                    matches.extend(sale_matches)
                    stats['sell_count'] += 1
                    stats['fifo_match_count'] += len(sale_matches)
                except ValueError as e:
                    issues.append(f"Error processing sale of {tx.ticker}: {str(e)}")

        # Create result
        result = FifoCalculationResult(
            matches=matches,
            portfolio=portfolio,
            stats=stats,
            issues=issues
        )

        return result
