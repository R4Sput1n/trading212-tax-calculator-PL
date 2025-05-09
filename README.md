# Trading212 Tax Calculator

A modular, object-oriented tool for calculating taxes for Trading212 transactions in Poland.

## Overview

This application processes CSV files exported from Trading212 and calculates tax data for Polish tax forms PIT-38 and PIT/ZG. It handles stock transactions (using FIFO method) and dividends, including foreign tax credits.

> **DISCLAIMER**: I am not a tax advisor. The Polish tax system can be overwhelming at times, and this tool is provided as-is without any warranty. For any tax advice or detailed information, please contact your local tax advisor or Krajową Informację Skarbową ([contact form](https://www.podatki.gov.pl/skontaktuj-sie-z-nami/pytanie-e-mail/masz-pytanie/)).

## Features

- Parsing Trading212 CSV export files
- Calculating stock sales using FIFO (First In, First Out) method
- Processing dividends and withholding taxes
- Converting foreign currencies to PLN using NBP exchange rates
- Generating tax data for PIT-38 and PIT/ZG forms
- Exporting tax data to Excel
- Filtering calculations by tax year

## Project Structure

The application follows SOLID principles and is organized into the following modules:

- `models/`: Data models for transactions, portfolio, etc.
- `parsers/`: CSV parsers and data processors
- `calculators/`: Tax calculation logic
- `services/`: External API services (exchange rates, company information)
- `exporters/`: Output generators for tax reports
- `utils/`: Utility functions
- `config/`: Application settings

## Requirements

- Python 3.7+
- Required Python packages:
  - pandas
  - openpyxl
  - requests
  - yfinance
  - python-dateutil

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/trading212-tax-calculator.git
   cd trading212-tax-calculator
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

The application can be run in different modes:

1. **Processing mode**: Process Trading212 CSV files and save to an intermediate file
   ```
   python main.py -m processing -i /path/to/trading212_files/*.csv -o data/processed_data.csv
   ```

2. **Calculation mode**: Calculate taxes based on the processed data
   ```
   python main.py -m calculation -i data/processed_data.csv -r output/tax_report.xlsx
   ```

3. **All-in-one mode**: Process files and calculate taxes in one step
   ```
   python main.py -m all -i /path/to/trading212_files/*.csv -o data/processed_data.csv -r output/tax_report.xlsx
   ```

### Command Line Arguments

- `-m, --mode`: Operating mode (`processing`, `calculation`, or `all`)
- `-i, --input`: Input file or directory with CSV files
- `-o, --output`: Path to output file (for processing mode)
- `-r, --report`: Path to tax report file (for calculation mode)
- `-y, --year`: Tax year to calculate (default: all years)
- `-v, --verbose`: Enable verbose output

## Example Workflow

1. Export your Trading212 history as CSV files
2. Run the application:
   ```
   python main.py -m all -i /path/to/trading212_export.csv -v
   ```
3. Review the generated tax report in `output/tax_report.xlsx`

4. For specific tax year calculation:
   ```
   python main.py -m all -i /path/to/trading212_export.csv -y 2024
   ```

## Tax Report Format

The tax report Excel file contains multiple sheets:

1. **PIT-38 - Akcje i Koszty**: Summary of stock transactions for PIT-38 form
2. **PIT-38 - Dywidendy**: Summary of dividend income for PIT-38 form (Section G)
3. **PIT-ZG**: Details for the PIT/ZG attachment (income from foreign sources)

## Architecture

The application follows object-oriented design principles and SOLID principles:

- **Single Responsibility**: Each class has a single responsibility
- **Open-Closed**: Components are open for extension but closed for modification
- **Liskov Substitution**: Services can be replaced with alternative implementations
- **Interface Segregation**: Interfaces are specific to client needs
- **Dependency Inversion**: High-level modules depend on abstractions

Key design patterns used:
- **Strategy Pattern**: For different calculation methods
- **Factory Pattern**: For creating services
- **Dependency Injection**: For providing services to clients
- **Repository Pattern**: For data access abstraction

## Development and Extension

To extend the application:

1. **Adding a new data source**: Implement a new parser class that extends `ParserInterface`
2. **Supporting new calculation methods**: Create a new calculator that implements `CalculatorInterface`
3. **Adding new export formats**: Implement a new exporter that extends `ExporterInterface`

## Testing

Run the test suite:

```
pytest tests/
```
There are no tests implemented at the moment.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributors

- [R4Sput1n](https://github.com/R4Sput1n) - Initial work
- [Claude 3.7 Sonnet](https://anthropic.com/claude) - Code refactoring, modularization, and documentation

## Acknowledgments

- [Artur Wiśniewski](https://stockbroker.pl/author/archislaw-makler/) for his [guide on ETF tax calculations in Poland](https://stockbroker.pl/etf-jak-rozliczac-podatki-przewodnik-krok-po-kroku/)

