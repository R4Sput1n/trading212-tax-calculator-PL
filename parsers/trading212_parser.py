import pandas as pd
from dateutil.parser import parse
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional
import glob
import logging
import os

from models.transaction import (
    Transaction, BuyTransaction, SellTransaction, 
    DividendTransaction, InterestTransaction
)
from parsers.parser_interface import ParserInterface
from services.exchange_rate_service import ExchangeRateService
from services.company_info_service import CompanyInfoService
from utils.exceptions import (
    FileNotFoundError as CustomFileNotFoundError,
    FileReadError,
    InvalidCSVFormatError,
    InvalidTransactionDataError,
    DateParsingError,
    NumberParsingError,
    handle_file_not_found,
    handle_parsing_error
)

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
        """
        Parse a single Trading212 CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of Transaction objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileReadError: If file cannot be read
            InvalidCSVFormatError: If CSV format is invalid
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise handle_file_not_found(file_path)
        
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            raise FileReadError(file_path, "File exists but cannot be read. Check permissions.")
        
        try:
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError:
            raise FileReadError(file_path, "File is empty.")
        except pd.errors.ParserError as e:
            raise InvalidCSVFormatError(file_path, reason=f"CSV parsing failed: {str(e)}")
        except Exception as e:
            raise FileReadError(file_path, f"Unexpected error reading file: {str(e)}")
        
        return self.parse_data(df, source_file=file_path)

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
    
    def _detect_csv_format(self, df: pd.DataFrame, source_file: str = None) -> str:
        """
        Detect whether the CSV is original Trading212 format or processed format.
        
        Args:
            df: DataFrame to check
            source_file: Optional source file path for error messages
        
        Returns:
            'original' for Trading212 CSV export
            'processed' for our intermediate processed CSV
            
        Raises:
            InvalidCSVFormatError: If format cannot be determined
        """
        # Original Trading212 CSV has 'Action' column
        if 'Action' in df.columns:
            return 'original'
        # Processed CSV has 'action' column (lowercase) that we add
        elif 'action' in df.columns:
            return 'processed'
        else:
            raise InvalidCSVFormatError(
                source_file or "unknown",
                reason="CSV format not recognized. Expected 'Action' column (Trading212 export) or 'action' column (processed CSV)."
            )
    
    def parse_data(self, df: pd.DataFrame, source_file: str = None) -> List[Transaction]:
        """
        Parse Trading212 data from a pandas DataFrame.
        Automatically detects whether it's an original or processed CSV.
        
        Args:
            df: DataFrame containing Trading212 transaction data
            source_file: Optional source file path for error messages
            
        Returns:
            List of Transaction objects
            
        Raises:
            InvalidCSVFormatError: If CSV format is invalid
        """
        # Check if DataFrame is empty
        if df.empty:
            logger.warning(f"Empty DataFrame provided{' from ' + source_file if source_file else ''}")
            return []
        
        csv_format = self._detect_csv_format(df, source_file)
        
        if csv_format == 'original':
            return self._parse_original_format(df, source_file)
        else:
            return self._parse_processed_format(df, source_file)
    
    def _parse_original_format(self, df: pd.DataFrame, source_file: str = None) -> List[Transaction]:
        """
        Parse original Trading212 CSV export format.
        
        Args:
            df: DataFrame containing Trading212 transaction data
            source_file: Optional source file path for error messages
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        errors = []
        row_number = 0
        
        for idx, row in df.iterrows():
            row_number = idx + 2  # +2 for header row and 0-indexing
            
            # Skip rows without Action
            if pd.isna(row.get('Action')):
                continue
                
            try:
                # Parse date field
                try:
                    date = parse(row['Time'])
                except (KeyError, ValueError, TypeError) as e:
                    raise DateParsingError(str(row.get('Time', 'N/A')))
                
                # Get action
                action = row['Action']
                
                # Parse string fields (safe)
                ticker = row.get('Ticker', '')
                name = row.get('Name', '')
                isin = row.get('ISIN', '')
                currency = row.get('Currency (Price / share)', 'PLN')
                
                # Parse numeric fields with error handling
                try:
                    quantity = Decimal(str(row['No. of shares'])) if pd.notna(row.get('No. of shares')) else Decimal('0')
                except (ValueError, InvalidOperation) as e:
                    raise NumberParsingError(str(row.get('No. of shares', 'N/A')), 'No. of shares')
                
                try:
                    price = Decimal(str(row['Price / share'])) if pd.notna(row.get('Price / share')) else Decimal('0')
                except (ValueError, InvalidOperation) as e:
                    raise NumberParsingError(str(row.get('Price / share', 'N/A')), 'Price / share')
                
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
            
            except (DateParsingError, NumberParsingError, InvalidTransactionDataError) as e:
                # These are our custom exceptions with good error messages
                error_msg = f"Row {row_number}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            except Exception as e:
                # Unexpected errors
                error_msg = f"Row {row_number}: Unexpected error - {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Log summary
        if errors:
            logger.warning(f"Parsed {len(transactions)} transactions with {len(errors)} errors")
            if len(errors) <= 5:
                for error in errors:
                    logger.warning(f"  - {error}")
            else:
                for error in errors[:3]:
                    logger.warning(f"  - {error}")
                logger.warning(f"  ... and {len(errors) - 3} more errors")
        
        return transactions
    
    def _parse_processed_format(self, df: pd.DataFrame, source_file: str = None) -> List[Transaction]:
        """
        Parse processed CSV format (our intermediate format with 'action' column).
        
        Args:
            df: DataFrame containing processed transaction data
            source_file: Optional source file path for error messages
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        errors = []
        row_number = 0
        
        for idx, row in df.iterrows():
            row_number = idx + 2  # +2 for header row and 0-indexing
            
            # Skip rows without action
            if pd.isna(row.get('action')):
                continue
                
            try:
                action = row['action']
                
                # Parse date field
                try:
                    date = parse(str(row['date']))
                except (KeyError, ValueError, TypeError) as e:
                    raise DateParsingError(str(row.get('date', 'N/A')))
                
                # Parse string fields (safe)
                ticker = row.get('ticker', '') if pd.notna(row.get('ticker')) else ''
                symbol = row.get('symbol', ticker) if pd.notna(row.get('symbol')) else ticker
                name = row.get('name', '') if pd.notna(row.get('name')) else ''
                isin = row.get('isin', '') if pd.notna(row.get('isin')) else ''
                currency = row.get('currency', 'PLN') if pd.notna(row.get('currency')) else 'PLN'
                
                # Parse numeric fields with error handling
                try:
                    quantity = Decimal(str(row['quantity'])) if pd.notna(row.get('quantity')) else Decimal('0')
                except (ValueError, InvalidOperation) as e:
                    raise NumberParsingError(str(row.get('quantity', 'N/A')), 'quantity')
                
                try:
                    price = Decimal(str(row['price_per_share'])) if pd.notna(row.get('price_per_share')) else Decimal('0')
                except (ValueError, InvalidOperation) as e:
                    raise NumberParsingError(str(row.get('price_per_share', 'N/A')), 'price_per_share')
                
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
            
            except (DateParsingError, NumberParsingError, InvalidTransactionDataError) as e:
                # These are our custom exceptions with good error messages
                error_msg = f"Row {row_number}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            except Exception as e:
                # Unexpected errors
                error_msg = f"Row {row_number}: Unexpected error - {type(e).__name__}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Log summary
        if errors:
            logger.warning(f"Parsed {len(transactions)} transactions with {len(errors)} errors")
            if len(errors) <= 5:
                for error in errors:
                    logger.warning(f"  - {error}")
            else:
                for error in errors[:3]:
                    logger.warning(f"  - {error}")
                logger.warning(f"  ... and {len(errors) - 3} more errors")
        
        return transactions
