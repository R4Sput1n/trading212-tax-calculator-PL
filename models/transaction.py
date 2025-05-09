from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List


@dataclass
class Transaction(ABC):
    """Base abstract class for all transaction types"""
    date: datetime
    ticker: str
    symbol: str
    isin: str
    name: str
    quantity: Decimal
    price_per_share: Decimal
    currency: str
    exchange_rate: Optional[Decimal] = None
    total_value_foreign: Optional[Decimal] = None
    total_value_pln: Optional[Decimal] = None
    fees_foreign: Optional[Decimal] = None
    fees_pln: Optional[Decimal] = None
    country: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    def get_transaction_type(self) -> str:
        """Returns the type of transaction"""
        pass
    
    def calculate_total_value_foreign(self) -> Decimal:
        """Calculate the total value in foreign currency"""
        return self.quantity * self.price_per_share
    
    def calculate_total_value_pln(self) -> Decimal:
        """Calculate the total value in PLN"""
        if self.exchange_rate is None:
            raise ValueError("Exchange rate is required to calculate PLN value")
        
        return self.calculate_total_value_foreign() * self.exchange_rate


@dataclass
class BuyTransaction(Transaction):
    """Class representing a buy transaction"""
    
    def get_transaction_type(self) -> str:
        return "BUY"


@dataclass
class SellTransaction(Transaction):
    """Class representing a sell transaction"""
    
    def get_transaction_type(self) -> str:
        return "SELL"


@dataclass
class DividendTransaction(Transaction):
    """Class representing a dividend transaction"""
    withholding_tax_foreign: Optional[Decimal] = None
    withholding_tax_pln: Optional[Decimal] = None
    
    def get_transaction_type(self) -> str:
        return "DIVIDEND"
    
    def calculate_net_dividend_foreign(self) -> Decimal:
        """Calculate the net dividend value in foreign currency"""
        if self.withholding_tax_foreign is None:
            return self.calculate_total_value_foreign()
        
        return self.calculate_total_value_foreign() - self.withholding_tax_foreign
    
    def calculate_net_dividend_pln(self) -> Decimal:
        """Calculate the net dividend value in PLN"""
        if self.exchange_rate is None:
            raise ValueError("Exchange rate is required to calculate PLN value")
        
        return self.calculate_net_dividend_foreign() * self.exchange_rate


@dataclass
class FifoMatchResult:
    """Represents a result of matching buy and sell transactions using FIFO"""
    sell_transaction: SellTransaction
    buy_transaction: BuyTransaction
    used_quantity: Decimal
    income_pln: Decimal
    cost_pln: Decimal
    profit_loss_pln: Decimal
    sell_date: datetime
    buy_date: datetime
    country: str
    ticker: str
