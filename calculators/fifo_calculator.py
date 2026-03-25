from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import logging

from models.transaction import Transaction, BuyTransaction, SellTransaction, FifoMatchResult
from models.portfolio import Portfolio
from calculators.calculator_interface import CalculatorInterface
from utils.exceptions import InsufficientSharesError, FIFOCalculationError

logger = logging.getLogger(__name__)


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
        Only validates BUY and SELL transactions since those are what FIFO processes.
        
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
        
        # Filter to only BUY and SELL transactions for validation
        buy_sell_transactions = [tx for tx in transactions 
                                  if isinstance(tx, (BuyTransaction, SellTransaction))]
        
        if not buy_sell_transactions:
            # No buy/sell transactions is not necessarily an error
            # (might just be dividends/interest)
            return issues
        
        # Check for transactions with missing required data
        for i, tx in enumerate(buy_sell_transactions):
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
        # Validate input data (collects warnings but doesn't stop processing)
        issues = self.validate(transactions)
        
        # Count transaction types for debugging
        buy_txs = [tx for tx in transactions if isinstance(tx, BuyTransaction)]
        sell_txs = [tx for tx in transactions if isinstance(tx, SellTransaction)]
        logger.info(f"FIFO Calculator: {len(transactions)} total, {len(buy_txs)} BUY, {len(sell_txs)} SELL")
        
        # Only return early if there are NO transactions at all
        if not transactions:
            return FifoCalculationResult(issues=issues if issues else ["No transactions to process"])

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
        skipped_sells = 0
        for tx in sorted_transactions:
            if isinstance(tx, BuyTransaction):
                portfolio.add_transaction(tx)
                stats['buy_count'] += 1

            elif isinstance(tx, SellTransaction):
                try:
                    sale_matches = portfolio.process_sale(tx)

                    # Skip this sale if it's not in the specified tax year
                    if tax_year is not None and tx.date.year != tax_year:
                        skipped_sells += 1
                        continue

                    matches.extend(sale_matches)
                    stats['sell_count'] += 1
                    stats['fifo_match_count'] += len(sale_matches)
                except InsufficientSharesError as e:
                    # User-friendly error message for insufficient shares
                    issues.append(f"Error processing sale of {tx.ticker} on {tx.date.strftime('%Y-%m-%d')}: {e.message}")
                    logger.warning(f"FIFO error for {tx.ticker}: {e}")
                except Exception as e:
                    # Unexpected errors
                    issues.append(f"Unexpected error processing sale of {tx.ticker} on {tx.date.strftime('%Y-%m-%d')}: {type(e).__name__}: {str(e)}")
                    logger.error(f"Unexpected FIFO error for {tx.ticker}: {type(e).__name__}: {e}")

        logger.info(f"FIFO: {stats['buy_count']} buys added, {stats['sell_count']} sells processed, {skipped_sells} sells skipped (wrong year), {stats['fifo_match_count']} matches")

        # Create result
        result = FifoCalculationResult(
            matches=matches,
            portfolio=portfolio,
            stats=stats,
            issues=issues
        )

        return result
