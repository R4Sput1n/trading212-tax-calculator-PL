import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from models.transaction import BuyTransaction, SellTransaction, FifoMatchResult


@dataclass
class PortfolioPosition:
    """A position in a portfolio representing shares of a specific ticker"""
    ticker: str
    purchases: List[BuyTransaction] = field(default_factory=list)
    
    def add_purchase(self, transaction: BuyTransaction) -> None:
        """Add a purchase transaction to this position"""
        self.purchases.append(transaction)
        # Sort by date to ensure FIFO order
        self.purchases.sort(key=lambda x: x.date)
    
    def get_total_shares(self) -> Decimal:
        """Get the total number of shares in this position"""
        return sum(purchase.quantity for purchase in self.purchases)


@dataclass
class Portfolio:
    """A portfolio containing multiple positions"""
    positions: Dict[str, PortfolioPosition] = field(default_factory=dict)
    
    def add_transaction(self, transaction: BuyTransaction) -> None:
        """Add a buy transaction to the portfolio"""
        ticker = transaction.ticker
        
        if ticker not in self.positions:
            self.positions[ticker] = PortfolioPosition(ticker)
        
        self.positions[ticker].add_purchase(transaction)
    
    def process_sale(self, sale: SellTransaction) -> List[FifoMatchResult]:
        """
        Process a sale transaction using FIFO method.
        Returns a list of FifoMatchResult objects representing the sale.
        """
        ticker = sale.ticker
        
        if ticker not in self.positions:
            raise ValueError(f"Cannot sell {ticker}: not in portfolio")
        
        position = self.positions[ticker]
        
        if position.get_total_shares() < sale.quantity:
            raise ValueError(f"Cannot sell {sale.quantity} shares of {ticker}: only {position.get_total_shares()} available")
        
        results = []
        remaining_shares = sale.quantity
        
        # Calculate the sale value per share in PLN
        sale_value_per_share_pln = sale.total_value_pln / sale.quantity
        
        # Loop through purchases until all sold shares are accounted for
        while remaining_shares > 0 and position.purchases:
            oldest_purchase = position.purchases[0]
            
            # How many shares we're selling from this purchase
            shares_from_purchase = min(remaining_shares, oldest_purchase.quantity)
            
            # Calculate the ratio of sold shares to purchased shares
            ratio = shares_from_purchase / oldest_purchase.quantity
            
            # Calculate the income, cost, and profit/loss
            income_pln = shares_from_purchase * sale_value_per_share_pln
            
            # Cost includes both purchase price and fees
            purchase_cost = (oldest_purchase.total_value_pln * ratio)
            purchase_fees = (oldest_purchase.fees_pln or Decimal(0)) * ratio
            sale_fees = (sale.fees_pln or Decimal(0)) * (shares_from_purchase / sale.quantity)
            
            total_cost = purchase_cost + purchase_fees + sale_fees
            profit_loss = income_pln - total_cost
            
            # Create a FIFO match result
            result = FifoMatchResult(
                sell_transaction=sale,
                buy_transaction=oldest_purchase,
                used_quantity=shares_from_purchase,
                income_pln=income_pln,
                cost_pln=total_cost,
                profit_loss_pln=profit_loss,
                sell_date=sale.date,
                buy_date=oldest_purchase.date,
                country=sale.country or "Unknown",
                ticker=ticker
            )
            
            results.append(result)
            
            # Update the purchase or remove it if fully used
            if shares_from_purchase < oldest_purchase.quantity:
                oldest_purchase.quantity -= shares_from_purchase
            else:
                position.purchases.pop(0)
            
            remaining_shares -= shares_from_purchase

            logger = logging.getLogger(__name__)
            logger.info(f"FIFO result for {sale.ticker}:")
            logger.info(f"  Income in PLN: {income_pln}")
            logger.info(f"  Purchase cost in PLN: {purchase_cost}")
            logger.info(f"  Purchase fees in PLN: {purchase_fees}")
            logger.info(f"  Sale fees in PLN: {sale_fees}")
            logger.info(f"  Total cost in PLN: {total_cost}")
            logger.info(f"  Profit/Loss in PLN: {profit_loss}")
        
        return results
