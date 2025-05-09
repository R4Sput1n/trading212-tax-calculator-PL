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
from exporters.tax_form_exporter import TaxFormGenerator, TaxFormExporter
from models.transaction import Transaction
from utils.logging_config import configure_logging


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
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
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

    # Convert to DataFrame for export in a safer way
    import pandas as pd

    # First, collect all possible attributes
    all_attrs = set()
    for tx in transactions:
        all_attrs.update(tx.__dict__.keys())

    # Now create data with None for missing attributes
    data = {attr: [] for attr in all_attrs}
    for tx in transactions:
        for attr in all_attrs:
            data[attr].append(tx.__dict__.get(attr))

    # Create DataFrame
    df = pd.DataFrame(data)

    # Save to CSV
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    df.to_csv(args.output, index=False)

    logger.info(f"Saved processed data to {args.output}")
    print(f"Processing completed. Processed data saved to {args.output}")

    return transactions


def calculation_mode(args, services, transactions=None):
    """Calculate taxes and generate report"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting calculation mode, input: {args.input}, report: {args.report}")
    
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
        logger.info(f"Loaded {len(transactions)} transactions from {args.input}")
    
    # Create calculators
    fifo_calculator = FifoCalculator()
    dividend_calculator = DividendCalculator(tax_rate=settings.DEFAULT_TAX_RATE)
    
    # Run calculations
    fifo_result = fifo_calculator.calculate(transactions)
    dividend_result = dividend_calculator.calculate(transactions)
    
    # Check for issues
    if fifo_result.issues:
        logger.warning("FIFO calculation issues:")
        for issue in fifo_result.issues:
            logger.warning(f"  - {issue}")
    
    if dividend_result.issues:
        logger.warning("Dividend calculation issues:")
        for issue in dividend_result.issues:
            logger.warning(f"  - {issue}")
    
    # Generate tax form data
    tax_form_generator = TaxFormGenerator(tax_rate=float(settings.DEFAULT_TAX_RATE))
    tax_form_data = tax_form_generator.generate_tax_forms(fifo_result, dividend_result)
    
    # Export tax form data
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    tax_form_exporter = TaxFormExporter()
    success = tax_form_exporter.export(tax_form_data, args.report)
    
    if success:
        logger.info(f"Saved tax report to {args.report}")
        print(f"Calculation completed. Tax report saved to {args.report}")
        
        # Print summary
        print("\nSUMMARY:")
        print(f"Income from securities: {tax_form_data.pit38.total_income:.2f} PLN")
        print(f"Costs: {tax_form_data.pit38.total_cost:.2f} PLN")
        
        if tax_form_data.pit38.profit > 0:
            print(f"Profit: {tax_form_data.pit38.profit:.2f} PLN")
        else:
            print(f"Loss: {tax_form_data.pit38.loss:.2f} PLN")
        
        print(f"Tax due: {tax_form_data.pit38.tax_due} PLN")
        
        if tax_form_data.pit38.dividend_data:
            print("\nDIVIDENDS:")
            for div in tax_form_data.pit38.dividend_data:
                print(f"  {div['country']}:")
                print(f"    Dividend: {div['dividend_amount']:.2f} PLN")
                print(f"    Tax paid abroad: {div['tax_paid_abroad']:.2f} PLN")
                print(f"    Tax to pay in Poland: {div['tax_to_pay']:.2f} PLN")
    else:
        logger.error(f"Failed to save tax report to {args.report}")
        print(f"Calculation completed, but failed to save tax report to {args.report}")
    
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
