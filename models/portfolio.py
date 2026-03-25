import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from models.transaction import BuyTransaction, SellTransaction, FifoMatchResult
from utils.exceptions import InsufficientSharesError, FIFOCalculationError

@dataclass
class TaxLot:
    """Represents a specific lot of purchased shares, keeping track of remaining quantity without mutating the original transaction."""
    transaction: BuyTransaction
    remaining_quantity: Decimal

    def get_proportional_value(self, used_quantity: Decimal, total_value: Optional[Decimal]) -> Decimal:
        """Calculates the proportional value based on the original transaction quantity."""
        if not total_value:
            return Decimal('0')
        return total_value * (used_quantity / self.transaction.quantity)

@dataclass
class PortfolioPosition:
    """A position in a portfolio representing shares of a specific ticker"""
    ticker: str
    purchases: List[TaxLot] = field(default_factory=list)
    
    def add_purchase(self, transaction: BuyTransaction) -> None:
        """Add a purchase transaction to this position"""
        lot = TaxLot(transaction=transaction, remaining_quantity=transaction.quantity)
        self.purchases.append(lot)
        # Sort by date to ensure FIFO order
        self.purchases.sort(key=lambda x: x.transaction.date)

    def get_total_shares(self) -> Decimal:
        """Get the total number of shares in this position"""
        return sum(lot.remaining_quantity for lot in self.purchases)

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
        
        Raises:
            InsufficientSharesError: If trying to sell more shares than available
            FIFOCalculationError: If other calculation errors occur
        """
        ticker = sale.ticker
        
        if ticker not in self.positions:
            raise InsufficientSharesError(ticker, 0, float(sale.quantity))
        
        position = self.positions[ticker]
        available_shares = position.get_total_shares()
        
        if available_shares < sale.quantity:
            raise InsufficientSharesError(ticker, float(available_shares), float(sale.quantity))
        
        results = []
        remaining_shares = sale.quantity
        
        # Calculate the sale value per share in PLN
        sale_value_per_share_pln = sale.total_value_pln / sale.quantity
        
        # Loop through purchases until all sold shares are accounted for
        while remaining_shares > 0 and position.purchases:
            oldest_lot = position.purchases[0]
            oldest_purchase = oldest_lot.transaction  # Zawsze nienaruszona, oryginalna transakcja

            # How many shares we're selling from this lot
            shares_from_purchase = min(remaining_shares, oldest_lot.remaining_quantity)

            # Calculate the ratio for the sale side (sell fees are still based on the sale transaction)
            sale_ratio = shares_from_purchase / sale.quantity

            # Calculate the income
            income_pln = shares_from_purchase * sale_value_per_share_pln

            purchase_cost = oldest_lot.get_proportional_value(shares_from_purchase, oldest_purchase.total_value_pln)

            # Calculate detailed buy fees based on the lot's original state
            buy_currency_conversion_fee = oldest_lot.get_proportional_value(shares_from_purchase,
                                                                            oldest_purchase.currency_conversion_fee_pln)
            buy_transaction_tax = oldest_lot.get_proportional_value(shares_from_purchase,
                                                                    oldest_purchase.transaction_tax_pln)
            buy_other_fees = oldest_lot.get_proportional_value(shares_from_purchase, oldest_purchase.other_fees_pln)

            # Calculate detailed sell fees
            sell_currency_conversion_fee = (sale.currency_conversion_fee_pln or Decimal('0')) * sale_ratio
            sell_transaction_tax = (sale.transaction_tax_pln or Decimal('0')) * sale_ratio
            sell_other_fees = (sale.other_fees_pln or Decimal('0')) * sale_ratio

            # Calculate total fees
            purchase_fees = buy_currency_conversion_fee + buy_transaction_tax + buy_other_fees
            sale_fees = sell_currency_conversion_fee + sell_transaction_tax + sell_other_fees

            # Calculate total cost and profit/loss
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
                ticker=ticker,
                # Add the new fields
                buy_price_pln=purchase_cost,
                sell_price_pln=income_pln,
                buy_currency_conversion_fee_pln=buy_currency_conversion_fee,
                buy_transaction_tax_pln=buy_transaction_tax,
                buy_other_fees_pln=buy_other_fees,
                sell_currency_conversion_fee_pln=sell_currency_conversion_fee,
                sell_transaction_tax_pln=sell_transaction_tax,
                sell_other_fees_pln=sell_other_fees
            )
            
            results.append(result)
            
            # Update the purchase or remove it if fully used
            if shares_from_purchase < oldest_lot.remaining_quantity:
                oldest_lot.remaining_quantity -= shares_from_purchase
            else:
                position.purchases.pop(0)

            remaining_shares -= shares_from_purchase

            logger = logging.getLogger(__name__)
            logger.debug(f"FIFO result for {sale.ticker}:")
            logger.debug(f"  Income in PLN: {income_pln}")
            logger.debug(f"  Purchase cost in PLN: {purchase_cost}")
            logger.debug(f"  Buy currency conversion fee: {buy_currency_conversion_fee}")
            logger.debug(f"  Buy transaction tax: {buy_transaction_tax}")
            logger.debug(f"  Buy other fees: {buy_other_fees}")
            logger.debug(f"  Sell currency conversion fee: {sell_currency_conversion_fee}")
            logger.debug(f"  Sell transaction tax: {sell_transaction_tax}")
            logger.debug(f"  Sell other fees: {sell_other_fees}")
            logger.debug(f"  Total cost in PLN: {total_cost}")
            logger.debug(f"  Profit/Loss in PLN: {profit_loss}")
        
        return results
