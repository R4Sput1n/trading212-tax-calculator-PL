#!/usr/bin/env python3
"""
Trading212 Tax Calculator - Main Module

A tool for calculating taxes for Trading212 transactions in Poland.
"""
import argparse
import logging
import os
import sys
from typing import List, Optional

from config.settings import settings
from parsers.trading212_parser import Trading212Parser
from services.exchange_rate_service import NBPExchangeRateService
from services.company_info_service import YFinanceCompanyInfoService
from services.isin_service import DefaultISINService
from calculators.fifo_calculator import FifoCalculator
from calculators.dividend_calculator import DividendCalculator
from calculators.interest_calculator import InterestCalculator
from exporters.tax_form_exporter import TaxFormGenerator, TaxFormExporter
from models.transaction import Transaction
from utils.logging_config import configure_logging
from exporters.reportlab_exporter import ReportLabExporter
from utils.env_config import load_personal_data


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description=f'{settings.APP_NAME} {settings.APP_VERSION}')
    
    parser.add_argument('-m', '--mode',
                        choices=['processing', 'calculation', 'all'],
                        default='processing',
                        help='Operating mode: processing for CSV files processing, '
                             'calculation for tax calculations, '
                             'all for both without interruption')
    
    parser.add_argument('-i', '--input', type=str, default=None,
                        help='Path to input file or directory with CSV files')
    
    parser.add_argument('-o', '--output', type=str, default=settings.DEFAULT_PROCESSED_FILE,
                        help=f'Path to output file (for processing mode, default: {settings.DEFAULT_PROCESSED_FILE})')
    
    parser.add_argument('-r', '--report', type=str, default=settings.DEFAULT_REPORT_FILE,
                        help=f'Path to tax report file (for calculation mode, default: {settings.DEFAULT_REPORT_FILE})')

    parser.add_argument('-y', '--year', type=int, default=None,
                        help='Tax year to calculate (default: all years)')

    parser.add_argument('--pdf-report', action='store_true', default=True,
                        help='Generate PDF report (default: enabled)')
    
    parser.add_argument('--no-pdf', action='store_true', default=False,
                        help='Disable PDF report generation')

    parser.add_argument('--env-file', type=str, default='.env',
                        help='Path to .env file with personal data (default: .env)')
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Handle PDF flag logic
    if args.no_pdf:
        args.pdf_report = False
    
    # Set default input path if not provided
    if args.input is None:
        if args.mode == 'processing':
            args.input = os.path.join(settings.DEFAULT_DATA_DIR, "*.csv")
        else:
            args.input = settings.DEFAULT_PROCESSED_FILE
    
    return args


def setup_services():
    """Set up services for the application"""
    from services.service_factory import ServiceFactory
    return ServiceFactory.create_all_services()


def processing_mode(args, services):
    """Process CSV files and save to output file"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting processing mode, input: {args.input}, output: {args.output}")

    # Create parser
    parser = Trading212Parser(
        exchange_rate_service=services['exchange_rate_service'],
        company_info_service=services['company_info_service']
    )

    # Parse files
    if os.path.isdir(args.input):
        input_path = os.path.join(args.input, "*.csv")
        transactions = parser.parse_glob(input_path)
    elif '*' in args.input:
        transactions = parser.parse_glob(args.input)
    elif os.path.isfile(args.input):
        transactions = parser.parse_file(args.input)
    else:
        logger.error(f"Input path not found: {args.input}")
        sys.exit(1)

    logger.info(f"Parsed {len(transactions)} transactions")
    
    # Log transaction type breakdown
    tx_types = {}
    for tx in transactions:
        tx_type = tx.get_transaction_type()
        tx_types[tx_type] = tx_types.get(tx_type, 0) + 1
    logger.info(f"Transaction breakdown: {tx_types}")

    # Convert to DataFrame for export
    import pandas as pd

    # Define the columns we want in the processed CSV (in order)
    columns = [
        'action',  # NEW: Transaction type (BUY, SELL, DIVIDEND, INTEREST)
        'date',
        'ticker',
        'symbol',
        'isin',
        'name',
        'quantity',
        'price_per_share',
        'currency',
        'exchange_rate',
        'total_value_foreign',
        'total_value_pln',
        'fees_foreign',
        'fees_pln',
        'currency_conversion_fee_pln',
        'transaction_tax_pln',
        'other_fees_pln',
        'country',
        'withholding_tax_foreign',
        'withholding_tax_pln',
        'raw_data',
    ]

    # Build data with explicit column handling
    data = []
    for tx in transactions:
        row = {
            'action': tx.get_transaction_type(),  # NEW: Add action column
            'date': tx.date,
            'ticker': tx.ticker,
            'symbol': tx.symbol,
            'isin': tx.isin,
            'name': tx.name,
            'quantity': tx.quantity,
            'price_per_share': tx.price_per_share,
            'currency': tx.currency,
            'exchange_rate': tx.exchange_rate,
            'total_value_foreign': tx.total_value_foreign,
            'total_value_pln': tx.total_value_pln,
            'fees_foreign': tx.fees_foreign,
            'fees_pln': tx.fees_pln,
            'currency_conversion_fee_pln': tx.currency_conversion_fee_pln,
            'transaction_tax_pln': tx.transaction_tax_pln,
            'other_fees_pln': tx.other_fees_pln,
            'country': tx.country,
            'withholding_tax_foreign': getattr(tx, 'withholding_tax_foreign', None),
            'withholding_tax_pln': getattr(tx, 'withholding_tax_pln', None),
            'raw_data': tx.raw_data,
        }
        data.append(row)

    # Create DataFrame with specific column order
    df = pd.DataFrame(data, columns=columns)

    # Save to CSV
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    df.to_csv(args.output, index=False)

    logger.info(f"Saved processed data to {args.output}")
    print(f"Processing completed. Processed data saved to {args.output}")
    print(f"  Total transactions: {len(transactions)}")
    for tx_type, count in tx_types.items():
        print(f"    {tx_type}: {count}")

    return transactions


def calculation_mode(args, services, transactions=None):
    """Calculate taxes and generate report"""
    logger = logging.getLogger(__name__)

    tax_year_info = f" for tax year {args.year}" if args.year else ""
    logger.info(f"Starting calculation mode{tax_year_info}, input: {args.input}, report: {args.report}")

    # If transactions not provided, load from input file
    if transactions is None:
        # Load processed data
        if not os.path.isfile(args.input):
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)

        import pandas as pd
        df = pd.read_csv(args.input)

        # Create parser
        parser = Trading212Parser(
            exchange_rate_service=services['exchange_rate_service'],
            company_info_service=services['company_info_service']
        )

        # Parse data
        transactions = parser.parse_data(df)

        if args.year:
            logger.info(f"Loaded {len(transactions)} transactions, will filter sales/dividends for year {args.year}")
        else:
            logger.info(f"Loaded {len(transactions)} transactions (all years)")

    # Create calculators
    fifo_calculator = FifoCalculator()
    dividend_calculator = DividendCalculator(tax_rate=settings.DEFAULT_TAX_RATE)
    interest_calculator = InterestCalculator(tax_rate=settings.DEFAULT_TAX_RATE)

    # Run calculations with optional year filtering
    fifo_result = fifo_calculator.calculate(transactions, tax_year=args.year)
    dividend_result = dividend_calculator.calculate(transactions, tax_year=args.year)
    interest_result = interest_calculator.calculate(transactions, tax_year=args.year)

    # Check for issues
    if fifo_result.issues:
        logger.warning("FIFO calculation issues:")
        for issue in fifo_result.issues:
            logger.warning(f"  - {issue}")

    if dividend_result.issues:
        logger.warning("Dividend calculation issues:")
        for issue in dividend_result.issues:
            logger.warning(f"  - {issue}")

    if interest_result.issues:
        logger.warning("Interest calculation issues:")
        for issue in interest_result.issues:
            logger.warning(f"  - {issue}")

    # Generate tax form data
    tax_form_generator = TaxFormGenerator(tax_rate=float(settings.DEFAULT_TAX_RATE))
    tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result, interest_result)

    # Include tax year in the report filename if specified
    if args.year:
        report_path = args.report
        if '.' in report_path:
            base, ext = os.path.splitext(report_path)
            report_path = f"{base}_{args.year}{ext}"
        else:
            report_path = f"{report_path}_{args.year}"
    else:
        report_path = args.report

    # Export tax form data to Excel
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    tax_form_exporter = TaxFormExporter()
    success = tax_form_exporter.export(tax_form_data, report_path)

    if success:
        logger.info(f"Saved tax report to {report_path}")
        tax_year_str = f" for {args.year}" if args.year else ""
        print(f"Calculation completed. Tax report{tax_year_str} saved to {report_path}")

        # Print summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        
        print("\nSECURITIES (FIFO):")
        print(f"  Income: {tax_form_data.pit38.total_income:.2f} PLN")
        print(f"  Costs: {tax_form_data.pit38.total_cost:.2f} PLN")
        if tax_form_data.pit38.profit > 0:
            print(f"  Profit: {tax_form_data.pit38.profit:.2f} PLN")
        else:
            print(f"  Loss: {tax_form_data.pit38.loss:.2f} PLN")
        print(f"  Tax due (19%): {tax_form_data.pit38.tax_due} PLN")

        if tax_form_data.pit38.dividend_data:
            print("\nDIVIDENDS:")
            total_div = sum(d['dividend_amount'] for d in tax_form_data.pit38.dividend_data)
            total_tax_paid = sum(d['tax_paid_abroad'] for d in tax_form_data.pit38.dividend_data)
            total_tax_to_pay = sum(d['tax_to_pay'] for d in tax_form_data.pit38.dividend_data)
            for div in tax_form_data.pit38.dividend_data:
                print(f"  {div['country']}:")
                print(f"    Dividend: {div['dividend_amount']:.2f} PLN")
                print(f"    Tax paid abroad: {div['tax_paid_abroad']:.2f} PLN")
                print(f"    Tax to pay in Poland: {div['tax_to_pay']:.2f} PLN")
            print(f"  TOTAL dividends: {total_div:.2f} PLN")
            print(f"  TOTAL tax to pay: {total_tax_to_pay:.2f} PLN")

        if hasattr(tax_form_data.pit38, 'interest_data') and tax_form_data.pit38.interest_data:
            print("\nINTEREST ON CASH:")
            print(f"  Total interest: {tax_form_data.pit38.interest_data['total_interest_pln']:.2f} PLN")
            print(f"  Tax due (19%): {tax_form_data.pit38.interest_data['tax_due']:.2f} PLN")
        
        print("\n" + "="*50)
    else:
        logger.error(f"Failed to save tax report to {report_path}")
        print(f"Calculation completed, but failed to save tax report to {report_path}")

    if args.pdf_report:
        # Determine PDF report path
        pdf_path = report_path
        if '.' in pdf_path:
            pdf_path = os.path.splitext(pdf_path)[0] + '.pdf'
        else:
            pdf_path = pdf_path + '.pdf'

        # Load personal data
        personal_data = load_personal_data(args.env_file)

        # Create PDF exporter
        pdf_exporter = ReportLabExporter(personal_data)

        # Export data
        pdf_data = {
            'tax_year': args.year,
            'fifo_result': fifo_result,
            'dividend_result': dividend_result,
            'interest_result': interest_result
        }

        pdf_exporter.export(pdf_data, pdf_path)

    return tax_form_data


def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(log_level, log_file=settings.DEFAULT_LOG_FILE)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.APP_NAME} {settings.APP_VERSION}")
    
    # Create default directories
    settings.init_directories()
    
    # Setup services
    services = setup_services()
    
    transactions = None
    
    # Run selected mode
    if args.mode == 'processing':
        transactions = processing_mode(args, services)
    elif args.mode == 'calculation':
        calculation_mode(args, services)
    elif args.mode == 'all':
        transactions = processing_mode(args, services)
        calculation_mode(args, services, transactions)
    
    logger.info("Program completed successfully")


if __name__ == "__main__":
    main()
