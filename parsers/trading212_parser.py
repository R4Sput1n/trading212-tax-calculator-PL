import pandas as pd
from dateutil.parser import parse
from decimal import Decimal
from typing import List, Dict, Any, Optional
import glob
import logging

from models.transaction import (
    Transaction, BuyTransaction, SellTransaction, 
    DividendTransaction, InterestTransaction
)
from parsers.parser_interface import ParserInterface
from services.exchange_rate_service import ExchangeRateService
from services.company_info_service import CompanyInfoService

logger = logging.getLogger(__name__)


class Trading212Parser(ParserInterface):
    """Parser for Trading212 CSV files"""
    
    # Map action strings to transaction types
    # Note: Trading212 has various order types - we need to catch all buy/sell variants
    ACTION_TO_TYPE = {
        # Buy orders
        'Market buy': 'BUY',
        'Limit buy': 'BUY',
        'Stop buy': 'BUY',
        'Stop limit buy': 'BUY',
        # Sell orders
        'Market sell': 'SELL',
        'Limit sell': 'SELL',
        'Stop sell': 'SELL',
        'Stop limit sell': 'SELL',
        # Dividends
        'Dividend (Ordinary)': 'DIVIDEND',
        'Dividend (Dividend)': 'DIVIDEND',
        'Dividend (Dividends paid by us corporations)': 'DIVIDEND',
        'Dividend (Dividends paid by foreign corporations)': 'DIVIDEND',
        'Dividend': 'DIVIDEND',
        # Interest
        'Interest on cash': 'INTEREST',
    }
    
    @classmethod
    def _get_transaction_type(cls, action: str) -> Optional[str]:
        """
        Get the transaction type for a given action string.
        Handles both exact matches and partial matches for flexibility.
        
        Args:
            action: The action string from Trading212 CSV
            
        Returns:
            Transaction type ('BUY', 'SELL', 'DIVIDEND', 'INTEREST') or None
        """
        # Try exact match first
        if action in cls.ACTION_TO_TYPE:
            return cls.ACTION_TO_TYPE[action]
        
        # Try case-insensitive match
        action_lower = action.lower()
        for key, value in cls.ACTION_TO_TYPE.items():
            if key.lower() == action_lower:
                return value
        
        # Try partial matching for buy/sell variants we might have missed
        if 'buy' in action_lower:
            return 'BUY'
        if 'sell' in action_lower:
            return 'SELL'
        if 'dividend' in action_lower:
            return 'DIVIDEND'
        if 'interest' in action_lower:
            return 'INTEREST'
        
        return None
    
    def __init__(
        self, 
        exchange_rate_service: ExchangeRateService,
        company_info_service: CompanyInfoService
    ):
        self.exchange_rate_service = exchange_rate_service
        self.company_info_service = company_info_service
    
    def parse_file(self, file_path: str) -> List[Transaction]:
        """Parse a single Trading212 CSV file"""
        df = pd.read_csv(file_path)
        return self.parse_data(df)

    def parse_files(self, file_paths: List[str]) -> List[Transaction]:
        """Parse multiple Trading212 CSV files with duplicate detection"""
        if not file_paths:
            return []

        all_transactions = []
        seen_transactions = set()  # Track unique transaction identifiers

        for file_path in file_paths:
            transactions = self.parse_file(file_path)

            for tx in transactions:
                # Create a unique identifier for the transaction
                # Using relevant fields that should be unique for each real transaction
                tx_id = (tx.date, tx.ticker, tx.get_transaction_type(),
                         tx.quantity, tx.price_per_share)

                # Only add if not seen before
                if tx_id not in seen_transactions:
                    seen_transactions.add(tx_id)
                    all_transactions.append(tx)
                else:
                    logger.debug(f"Skipping duplicate transaction: {tx.date} {tx.ticker} {tx.get_transaction_type()}")

        # Sort by date
        all_transactions.sort(key=lambda x: x.date)
        return all_transactions
    
    def parse_glob(self, glob_pattern: str) -> List[Transaction]:
        """Parse all files matching a glob pattern"""
        file_paths = glob.glob(glob_pattern)
        return self.parse_files(file_paths)
    
    def _detect_csv_format(self, df: pd.DataFrame) -> str:
        """
        Detect whether the CSV is original Trading212 format or processed format.
        
        Returns:
            'original' for Trading212 CSV export
            'processed' for our intermediate processed CSV
        """
        # Original Trading212 CSV has 'Action' column
        if 'Action' in df.columns:
            return 'original'
        # Processed CSV has 'action' column (lowercase) that we add
        elif 'action' in df.columns:
            return 'processed'
        else:
            raise ValueError(
                "CSV format not recognized. Expected 'Action' column (Trading212 export) "
                "or 'action' column (processed CSV)."
            )
    
    def parse_data(self, df: pd.DataFrame) -> List[Transaction]:
        """
        Parse Trading212 data from a pandas DataFrame.
        Automatically detects whether it's an original or processed CSV.
        
        Args:
            df: DataFrame containing Trading212 transaction data
            
        Returns:
            List of Transaction objects
        """
        csv_format = self._detect_csv_format(df)
        
        if csv_format == 'original':
            return self._parse_original_format(df)
        else:
            return self._parse_processed_format(df)
    
    def _parse_original_format(self, df: pd.DataFrame) -> List[Transaction]:
        """
        Parse original Trading212 CSV export format.
        
        Args:
            df: DataFrame containing Trading212 transaction data
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        
        for _, row in df.iterrows():
            # Skip rows without Action
            if pd.isna(row.get('Action')):
                continue
                
            try:
                # Parse common fields
                date = parse(row['Time'])
                action = row['Action']
                ticker = row.get('Ticker', '')
                name = row.get('Name', '')
                isin = row.get('ISIN', '')
                quantity = Decimal(str(row['No. of shares'])) if pd.notna(row.get('No. of shares')) else Decimal('0')
                price = Decimal(str(row['Price / share'])) if pd.notna(row.get('Price / share')) else Decimal('0')
                currency = row.get('Currency (Price / share)', 'PLN')
                
                # Skip non-investment transactions
                tx_type = self._get_transaction_type(action)
                if tx_type is None:
                    logger.debug(f"Skipping unknown action type: {action}")
                    continue
                
                # Get exchange rate if not PLN
                exchange_rate = None
                if currency != 'PLN' and pd.notna(currency):
                    exchange_rate = self.exchange_rate_service.get_exchange_rate(date, currency)
                    exchange_rate = Decimal(str(exchange_rate)) if exchange_rate else None
                else:
                    exchange_rate = Decimal('1.0')
                
                # Calculate total value in foreign currency and PLN
                total_value_foreign = quantity * price
                total_value_pln = total_value_foreign * exchange_rate if exchange_rate else None

                fees_foreign = Decimal('0')
                fees_pln = Decimal('0')
                currency_conversion_fee_pln = Decimal('0')
                transaction_tax_pln = Decimal('0')
                other_fees_pln = Decimal('0')

                # Handle Currency conversion fee
                if pd.notna(row.get('Currency conversion fee')):
                    fee_amount = Decimal(str(row['Currency conversion fee']))
                    fee_currency = row.get('Currency (Currency conversion fee)', 'PLN')

                    if fee_currency == 'PLN':
                        fees_pln += fee_amount
                        currency_conversion_fee_pln += fee_amount
                    else:
                        fee_amount_pln = fee_amount * exchange_rate if exchange_rate else Decimal('0')
                        fees_foreign += fee_amount
                        currency_conversion_fee_pln += fee_amount_pln

                # Handle French transaction tax
                if pd.notna(row.get('French transaction tax')):
                    tax_amount = Decimal(str(row['French transaction tax']))
                    tax_currency = row.get('Currency (French transaction tax)', 'PLN')

                    if tax_currency == 'PLN':
                        fees_pln += tax_amount
                        transaction_tax_pln += tax_amount
                    else:
                        tax_amount_pln = tax_amount * exchange_rate if exchange_rate else Decimal('0')
                        fees_foreign += tax_amount
                        transaction_tax_pln += tax_amount_pln

                # Convert foreign fees to PLN
                if fees_foreign > 0 and exchange_rate:
                    fees_pln += fees_foreign * exchange_rate
                
                # Get company country
                country = None
                if pd.notna(isin) and pd.notna(name):
                    country = self.company_info_service.get_company_country(isin, name)
                
                # Create transaction based on type
                transaction = None
                
                if tx_type == 'BUY':
                    transaction = BuyTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=ticker,  # Symbol and ticker are the same in Trading212
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        raw_data=row.to_dict()
                    )
                
                elif tx_type == 'SELL':
                    transaction = SellTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=ticker,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        fees_pln=fees_pln,
                        country=country,
                        raw_data=row.to_dict()
                    )
                
                elif tx_type == 'DIVIDEND':
                    withholding_tax_foreign = None
                    withholding_tax_pln = None
                    
                    if pd.notna(row.get('Withholding tax')):
                        withholding_tax_foreign = Decimal(str(row['Withholding tax']))
                        withholding_tax_pln = withholding_tax_foreign * exchange_rate if exchange_rate else None
                    
                    transaction = DividendTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=ticker,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        withholding_tax_foreign=withholding_tax_foreign,
                        withholding_tax_pln=withholding_tax_pln,
                        raw_data=row.to_dict()
                    )
                
                elif tx_type == 'INTEREST':
                    # For interest, the "Total" column contains the interest amount
                    interest_amount = Decimal(str(row.get('Total', 0))) if pd.notna(row.get('Total')) else Decimal('0')
                    interest_currency = row.get('Currency (Total)', 'PLN')
                    
                    # Get exchange rate for interest currency
                    if interest_currency != 'PLN' and pd.notna(interest_currency):
                        interest_exchange_rate = self.exchange_rate_service.get_exchange_rate(date, interest_currency)
                        interest_exchange_rate = Decimal(str(interest_exchange_rate)) if interest_exchange_rate else Decimal('1.0')
                    else:
                        interest_exchange_rate = Decimal('1.0')
                    
                    interest_pln = interest_amount * interest_exchange_rate
                    
                    transaction = InterestTransaction(
                        date=date,
                        ticker='INTEREST',
                        symbol='INTEREST',
                        isin='',
                        name='Interest on cash',
                        quantity=Decimal('1'),  # Use 1 as quantity for interest
                        price_per_share=interest_amount,
                        currency=interest_currency if pd.notna(interest_currency) else 'PLN',
                        exchange_rate=interest_exchange_rate,
                        total_value_foreign=interest_amount,
                        total_value_pln=interest_pln,
                        fees_foreign=Decimal('0'),
                        fees_pln=Decimal('0'),
                        currency_conversion_fee_pln=Decimal('0'),
                        transaction_tax_pln=Decimal('0'),
                        other_fees_pln=Decimal('0'),
                        country='Poland',  # Interest is from T212 which is based in... actually let's use source
                        raw_data=row.to_dict()
                    )
                
                if transaction:
                    transactions.append(transaction)
            
            except Exception as e:
                logger.error(f"Error processing row: {e}")
                continue
        
        return transactions
    
    def _parse_processed_format(self, df: pd.DataFrame) -> List[Transaction]:
        """
        Parse processed CSV format (our intermediate format with 'action' column).
        
        Args:
            df: DataFrame containing processed transaction data
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        
        for _, row in df.iterrows():
            # Skip rows without action
            if pd.isna(row.get('action')):
                continue
                
            try:
                action = row['action']
                
                # Parse common fields
                date = parse(str(row['date']))
                ticker = row.get('ticker', '') if pd.notna(row.get('ticker')) else ''
                symbol = row.get('symbol', ticker) if pd.notna(row.get('symbol')) else ticker
                name = row.get('name', '') if pd.notna(row.get('name')) else ''
                isin = row.get('isin', '') if pd.notna(row.get('isin')) else ''
                quantity = Decimal(str(row['quantity'])) if pd.notna(row.get('quantity')) else Decimal('0')
                price = Decimal(str(row['price_per_share'])) if pd.notna(row.get('price_per_share')) else Decimal('0')
                currency = row.get('currency', 'PLN') if pd.notna(row.get('currency')) else 'PLN'
                
                # Get exchange rate (already calculated in processed file)
                exchange_rate = Decimal(str(row['exchange_rate'])) if pd.notna(row.get('exchange_rate')) else Decimal('1.0')
                
                # Get pre-calculated values
                total_value_foreign = Decimal(str(row['total_value_foreign'])) if pd.notna(row.get('total_value_foreign')) else Decimal('0')
                total_value_pln = Decimal(str(row['total_value_pln'])) if pd.notna(row.get('total_value_pln')) else Decimal('0')
                fees_foreign = Decimal(str(row['fees_foreign'])) if pd.notna(row.get('fees_foreign')) else Decimal('0')
                fees_pln = Decimal(str(row['fees_pln'])) if pd.notna(row.get('fees_pln')) else Decimal('0')
                currency_conversion_fee_pln = Decimal(str(row['currency_conversion_fee_pln'])) if pd.notna(row.get('currency_conversion_fee_pln')) else Decimal('0')
                transaction_tax_pln = Decimal(str(row['transaction_tax_pln'])) if pd.notna(row.get('transaction_tax_pln')) else Decimal('0')
                other_fees_pln = Decimal(str(row['other_fees_pln'])) if pd.notna(row.get('other_fees_pln')) else Decimal('0')
                country = row.get('country', None) if pd.notna(row.get('country')) else None
                
                # Create transaction based on type
                transaction = None
                
                if action == 'BUY':
                    transaction = BuyTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=symbol,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        raw_data=None
                    )
                
                elif action == 'SELL':
                    transaction = SellTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=symbol,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        raw_data=None
                    )
                
                elif action == 'DIVIDEND':
                    withholding_tax_foreign = Decimal(str(row['withholding_tax_foreign'])) if pd.notna(row.get('withholding_tax_foreign')) else None
                    withholding_tax_pln = Decimal(str(row['withholding_tax_pln'])) if pd.notna(row.get('withholding_tax_pln')) else None
                    
                    transaction = DividendTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=symbol,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        withholding_tax_foreign=withholding_tax_foreign,
                        withholding_tax_pln=withholding_tax_pln,
                        raw_data=None
                    )
                
                elif action == 'INTEREST':
                    transaction = InterestTransaction(
                        date=date,
                        ticker=ticker,
                        symbol=symbol,
                        isin=isin,
                        name=name,
                        quantity=quantity,
                        price_per_share=price,
                        currency=currency,
                        exchange_rate=exchange_rate,
                        total_value_foreign=total_value_foreign,
                        total_value_pln=total_value_pln,
                        fees_foreign=fees_foreign,
                        fees_pln=fees_pln,
                        currency_conversion_fee_pln=currency_conversion_fee_pln,
                        transaction_tax_pln=transaction_tax_pln,
                        other_fees_pln=other_fees_pln,
                        country=country,
                        raw_data=None
                    )
                
                if transaction:
                    transactions.append(transaction)
            
            except Exception as e:
                logger.error(f"Error processing processed row: {e}")
                continue
        
        return transactions
