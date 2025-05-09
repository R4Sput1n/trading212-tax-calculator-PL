import pandas as pd
from dateutil.parser import parse
from decimal import Decimal
from typing import List, Dict, Any, Optional
import glob

from models.transaction import Transaction, BuyTransaction, SellTransaction, DividendTransaction
from parsers.parser_interface import ParserInterface
from services.exchange_rate_service import ExchangeRateService
from services.company_info_service import CompanyInfoService


class Trading212Parser(ParserInterface):
    """Parser for Trading212 CSV files"""
    
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
        """Parse multiple Trading212 CSV files"""
        if not file_paths:
            return []
        
        all_transactions = []
        for file_path in file_paths:
            transactions = self.parse_file(file_path)
            all_transactions.extend(transactions)
        
        # Sort by date
        all_transactions.sort(key=lambda x: x.date)
        return all_transactions
    
    def parse_glob(self, glob_pattern: str) -> List[Transaction]:
        """Parse all files matching a glob pattern"""
        file_paths = glob.glob(glob_pattern)
        return self.parse_files(file_paths)
    
    def parse_data(self, df: pd.DataFrame) -> List[Transaction]:
        """
        Parse Trading212 data from a pandas DataFrame
        
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
                
                # Get exchange rate if not PLN
                exchange_rate = None
                if currency != 'PLN':
                    exchange_rate = self.exchange_rate_service.get_exchange_rate(date, currency)
                    exchange_rate = Decimal(str(exchange_rate)) if exchange_rate else None
                else:
                    exchange_rate = Decimal('1.0')
                
                # Calculate total value in foreign currency and PLN
                total_value_foreign = quantity * price
                total_value_pln = total_value_foreign * exchange_rate if exchange_rate else None

                # Calculate fees
                fees_foreign = Decimal('0')
                fees_pln = Decimal('0')

                # Handle Currency conversion fee
                if pd.notna(row.get('Currency conversion fee')):
                    fee_amount = Decimal(str(row['Currency conversion fee']))
                    fee_currency = row.get('Currency (Currency conversion fee)', 'PLN')

                    if fee_currency == 'PLN':
                        fees_pln += fee_amount
                    else:
                        fees_foreign += fee_amount

                # Handle French transaction tax
                if pd.notna(row.get('French transaction tax')):
                    tax_amount = Decimal(str(row['French transaction tax']))
                    tax_currency = row.get('Currency (French transaction tax)', 'PLN')

                    if tax_currency == 'PLN':
                        fees_pln += tax_amount
                    else:
                        fees_foreign += tax_amount

                # Convert foreign fees to PLN
                if fees_foreign > 0 and exchange_rate:
                    fees_pln += fees_foreign * exchange_rate
                
                # Get company country
                country = None
                if pd.notna(isin) and pd.notna(name):
                    country = self.company_info_service.get_company_country(isin, name)
                
                # Create transaction based on type
                transaction = None
                
                if action in ['Market buy', 'Limit buy']:
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
                        country=country,
                        raw_data=row.to_dict()
                    )
                
                elif action in ['Market sell', 'Limit sell']:
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
                        fees_pln=fees_pln,
                        country=country,
                        raw_data=row.to_dict()
                    )
                
                elif 'Dividend' in action:
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
                        country=country,
                        withholding_tax_foreign=withholding_tax_foreign,
                        withholding_tax_pln=withholding_tax_pln,
                        raw_data=row.to_dict()
                    )
                
                if transaction:
                    transactions.append(transaction)
            
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return transactions
