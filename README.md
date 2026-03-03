# Trading212 Tax Calculator for Poland

A comprehensive, modular tool for calculating Polish taxes on Trading212 investment transactions with full PIT-38 and PIT/ZG form support.

## Overview

This application processes CSV files exported from Trading212 and generates complete tax reports for Polish tax forms **PIT-38** and **PIT/ZG**. It handles:
- Stock transactions using **FIFO (First In, First Out)** method
- **Dividend income** with foreign tax credit calculations
- **Interest on cash** (Trading212 cash interest)
- **Double taxation treaties (UPO)** - automatic verification for 90+ countries
- **Polish character support** in PDF reports

The tool generates both **Excel** and **PDF** reports with detailed instructions on how to fill out your tax forms.

> **DISCLAIMER**: I am not a tax advisor. The Polish tax system can be complex, and this tool is provided as-is without any warranty. For professional tax advice, please contact your local tax advisor or Krajowa Administracja Skarbowa ([KAS contact](https://www.podatki.gov.pl/skontaktuj-sie-z-nami/)).

## ✨ Key Features

### Core Functionality
- ✅ **FIFO Stock Calculations** - Automatic matching of buy/sell transactions
- ✅ **Dividend Processing** - Full foreign tax credit support
- ✅ **Interest Calculations** - Trading212 cash interest tracking
- ✅ **Multi-Currency Support** - Automatic NBP exchange rate fetching (GBP, USD, EUR, GBX, etc.)
- ✅ **Tax Year Filtering** - Calculate taxes for specific years

### Polish Tax Compliance
- ✅ **Double Taxation Treaties (UPO)** - Automatic verification for 90+ countries
  - Countries **WITH** treaty: Foreign tax is deductible
  - Countries **WITHOUT** treaty: Full 19% tax due in Poland (foreign tax NOT deductible)
- ✅ **NBP Exchange Rates** - Uses official rates from previous business day (as required by law)
- ✅ **PIT-38 Form Data** - Complete sections C, D, and G
- ✅ **PIT/ZG Attachment** - Breakdown by country for foreign income

### Reports & Output
- ✅ **Excel Reports** - Detailed breakdown with all transactions
- ✅ **PDF Reports** - Professional, printable reports with Polish character support (ą, ć, ę, ł, ń, ó, ś, ź, ż)
- ✅ **Clear Instructions** - Exact field-by-field guidance for filling out PIT-38
- ✅ **Summary Section** - "What to write where" with final tax amounts

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

- **Python 3.9+**
- **uv** (recommended package manager) or pip
- Required Python packages:
  - pandas
  - openpyxl
  - reportlab (for PDF generation)
  - requests
  - yfinance
  - python-dateutil
  - python-dotenv
  - peewee (for caching)

## Installation

### Method 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/R4Sput1n/trading212-tax-calculator-PL.git
cd trading212-tax-calculator-PL

# Install dependencies (uv automatically creates a virtual environment)
uv sync

# Run the application
uv run python main.py --help
```

### Method 2: Using pip

```bash
# Clone the repository
git clone https://github.com/R4Sput1n/trading212-tax-calculator-PL.git
cd trading212-tax-calculator-PL

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run the application
python main.py --help
```

### Optional: Polish Font Support for PDF

For proper Polish character rendering in PDF reports, install DejaVu fonts:

```bash
# macOS (using Homebrew)
brew install --cask font-dejavu

# Ubuntu/Debian
sudo apt-get install fonts-dejavu

# Fedora/RHEL
sudo dnf install dejavu-sans-fonts
```

The application will automatically detect and use available fonts. Supported fonts:
- DejaVu Sans (best Polish support)
- Arial Unicode (macOS default)
- Liberation Sans (Linux)
- Arial (Windows)

## Usage

### Quick Start

1. **Export your Trading212 transaction history**
   - Log in to Trading212
   - Go to History → Export
   - Download CSV file(s)
   - Place them in the `data/` folder

2. **Run the calculator**
   ```bash
   # Using uv (recommended)
   uv run python main.py -m all -i data/*.csv -y 2025

   # Or using regular python
   python main.py -m all -i data/*.csv -y 2025
   ```

3. **Check your reports**
   - Excel: `output/tax_report_2025.xlsx`
   - PDF: `output/tax_report_2025.pdf`

### Operating Modes

The application has three modes:

#### 1. Processing Mode
Process Trading212 CSV files and save enriched data:
```bash
python main.py -m processing -i data/*.csv -o output/processed_data.csv
```

#### 2. Calculation Mode
Calculate taxes from previously processed data:
```bash
python main.py -m calculation -i output/processed_data.csv -r output/tax_report.xlsx -y 2025
```

#### 3. All-in-One Mode (Recommended)
Process and calculate in one step:
```bash
python main.py -m all -i data/*.csv -y 2025
```

### Command Line Arguments

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--mode` | `-m` | Operating mode: `processing`, `calculation`, or `all` | `-m all` |
| `--input` | `-i` | Input CSV file(s) or directory | `-i data/*.csv` |
| `--output` | `-o` | Processed data output path (processing mode) | `-o output/processed.csv` |
| `--report` | `-r` | Tax report output path (calculation mode) | `-r output/report.xlsx` |
| `--year` | `-y` | Tax year to calculate | `-y 2025` |
| `--verbose` | `-v` | Enable detailed logging | `-v` |
| `--pdf-report` | | Generate PDF report (default: enabled) | `--pdf-report` |
| `--no-pdf` | | Disable PDF report generation | `--no-pdf` |
| `--env-file` | | Path to .env file with personal data | `--env-file .env` |

### Personal Data Configuration (Optional)

For personalized PDF reports, create a `.env` file in the project root:

```bash
# .env file
FULLNAME=Jan Kowalski
PESEL=12345678901
ADDRESS=ul. Przykładowa 123
CITY=Warszawa
POSTAL_CODE=00-001
TAX_OFFICE=Pierwszy Urząd Skarbowy Warszawa-Śródmieście
```

### Examples

**Calculate taxes for 2025:**
```bash
python main.py -m all -i data/2025_history.csv -y 2025
```

**Process multiple CSV files:**
```bash
python main.py -m all -i data/*.csv -y 2025 -v
```

**Generate only Excel report (no PDF):**
```bash
python main.py -m all -i data/*.csv -y 2025 --no-pdf
```

**Process data without calculating taxes:**
```bash
python main.py -m processing -i data/*.csv -o output/processed.csv
```

## Output Reports

The application generates comprehensive tax reports in two formats:

### Excel Report (`tax_report_YYYY.xlsx`)

Multiple sheets with detailed data:

1. **PIT-38 - Akcje**
   - Section C: Income and costs from stock sales (FIFO)
   - Section D: Tax base and tax due (19%)
   - Exact field numbers (C.22, C.23, D.29, D.31, etc.)

2. **PIT-38 - Dywidendy**
   - Section G: Foreign dividends by country
   - Tax treaty status (UPO) for each country
   - Foreign tax paid and deductible amounts
   - Final tax due in Poland

3. **PIT-38 - Odsetki** (if applicable)
   - Interest on cash from Trading212
   - 19% tax calculation
   - Instructions for PIT-38 inclusion

4. **PIT/ZG**
   - Breakdown by country for all foreign income
   - Income, costs, and profit per country
   - Required for PIT-38 attachment

### PDF Report (`tax_report_YYYY.pdf`)

Professional, printable report with Polish character support:

**Section 1: FIFO Stock Transactions**
- All buy transactions with NBP exchange rates
- All sell transactions with matched buys
- FIFO matching details (which buy matches which sell)
- Transaction-by-transaction breakdown
- Profit/loss calculations

**Section 2: Dividend Income**
- Summary table by country with UPO status
- Detailed transactions for each country
- Foreign tax paid vs. tax due in Poland
- **Important**: Countries WITHOUT tax treaty (UPO = NIE) pay full 19% in Poland!

**Section 3: Interest on Cash**
- Total interest earned on Trading212 cash account
- 19% tax calculation

**Section 4: Tax Form Instructions** ⭐
- **4.1**: Exact PIT-38 fields (C.22, C.23, D.29, D.31)
- **4.2**: PIT-38 Section G (dividends by country)
- **4.3**: PIT/ZG attachment data
- **4.4**: **Final Summary - "What to Write Where"**
  - Complete table with all amounts
  - Field-by-field instructions
  - Grand total tax to pay
  - Important reminders about tax treaties

### Console Output

Real-time summary displayed in terminal:

```
SECURITIES (FIFO):
  Income: 15,234.80 PLN
  Costs: 12,450.30 PLN
  Profit: 2,784.50 PLN
  Tax due (19%): 529 PLN

DIVIDENDS:
  United States [UPO: TAK]:
    Dividend: 450.25 PLN
    Tax to pay in Poland: 32.15 PLN
  Germany [UPO: TAK]:
    Dividend: 123.40 PLN
    Tax to pay in Poland: 8.45 PLN
  Colombia [BRAK UPO - pełne 19%!]:
    Dividend: 89.50 PLN
    Tax to pay in Poland: 17.01 PLN
  TOTAL tax to pay: 57.61 PLN

INTEREST ON CASH:
  Total interest: 245.80 PLN
  Tax due (19%): 46.70 PLN
```

## Important: Double Taxation Treaties (UPO)

The calculator automatically checks if countries have **double taxation treaties (Umowa o Unikaniu Podwójnego Opodatkowania - UPO)** with Poland.

### Countries WITH Tax Treaty ✅

For these countries, **foreign tax is deductible** from Polish 19% tax:

Poland has tax treaties with 90+ countries including:
- 🇺🇸 United States
- 🇩🇪 Germany
- 🇬🇧 United Kingdom
- 🇫🇷 France
- 🇯🇵 Japan
- 🇨🇦 Canada
- 🇨🇭 Switzerland
- 🇳🇱 Netherlands
- 🇸🇬 Singapore
- 🇦🇺 Australia
- And many more...

**Example**: US dividend of 100 PLN with 15% foreign tax (15 PLN):
- Polish tax due: 19% × 100 PLN = 19 PLN
- Foreign tax paid: 15 PLN
- **To pay in Poland: 19 - 15 = 4 PLN** ✅

### Countries WITHOUT Tax Treaty ❌

For these countries, you pay **FULL 19% tax in Poland**, regardless of foreign tax paid:

Examples:
- 🇨🇴 Colombia
- 🇻🇪 Venezuela
- 🇦🇷 Argentina (check current status)
- Most African countries (except those listed with treaties)

**Example**: Colombian dividend of 100 PLN with 20% foreign tax (20 PLN):
- Polish tax due: 19% × 100 PLN = 19 PLN
- Foreign tax paid: 20 PLN (NOT deductible!)
- **To pay in Poland: 19 PLN** ❌ (full amount)

The calculator **automatically detects** treaty status and shows clear warnings in reports!

## How It Works

### 1. Data Processing
- Reads Trading212 CSV exports
- Fetches NBP exchange rates for each transaction (previous business day)
- Enriches data with company country information (via yfinance)
- Validates and categorizes transactions

### 2. FIFO Calculation
- Maintains a portfolio state (queue of purchases per ticker)
- Matches sells with oldest buys (FIFO)
- Calculates profit/loss for each match
- Allocates fees proportionally

### 3. Dividend & Interest Processing
- Groups dividends by country
- Checks tax treaty status (UPO)
- Calculates foreign tax credit (if applicable)
- Processes cash interest (19% flat tax)

### 4. Tax Form Generation
- Aggregates all data into PIT-38 sections
- Prepares PIT/ZG attachment
- Generates detailed reports (Excel + PDF)

### 5. NBP Exchange Rate Rules
- Uses rate from **business day BEFORE** transaction date
- Automatic fallback for weekends/holidays (up to 7 days)
- Special handling for GBX (British pence) → converts to GBP first

## Architecture

The application follows **SOLID principles** and clean architecture:

### Layered Architecture

```
┌─────────────────────────────────────────┐
│ CLI (main.py)                           │
├─────────────────────────────────────────┤
│ Layer 1: Parsers                        │
│  → Trading212Parser                     │
├─────────────────────────────────────────┤
│ Layer 2: Calculators                    │
│  → FifoCalculator                       │
│  → DividendCalculator                   │
│  → InterestCalculator                   │
├─────────────────────────────────────────┤
│ Layer 3: Tax Form Generator             │
│  → TaxFormGenerator                     │
├─────────────────────────────────────────┤
│ Layer 4: Exporters                      │
│  → TaxFormExporter (Excel)              │
│  → ReportLabExporter (PDF)              │
└─────────────────────────────────────────┘
         ↓ uses
┌─────────────────────────────────────────┐
│ Services (External APIs)                │
│  → ExchangeRateService (NBP API)        │
│  → CompanyInfoService (yfinance)        │
└─────────────────────────────────────────┘
```

### Key Design Patterns
- **Strategy Pattern**: Different calculators implement `CalculatorInterface`
- **Factory Pattern**: `ServiceFactory` creates services
- **Dependency Injection**: Services injected into parsers/calculators
- **Template Method**: Exporters extend `ExporterInterface`

## Development

### Project Structure

```
trading212-tax-calculator-PL/
├── calculators/          # Tax calculation logic
│   ├── fifo_calculator.py
│   ├── dividend_calculator.py
│   └── interest_calculator.py
├── config/              # Settings and configuration
│   ├── settings.py
│   └── tax_treaties.py  # Countries with UPO
├── exporters/           # Report generators
│   ├── tax_form_exporter.py  (Excel)
│   └── reportlab_exporter.py (PDF)
├── models/              # Data models
│   ├── transaction.py
│   └── portfolio.py
├── parsers/             # CSV parsing
│   └── trading212_parser.py
├── services/            # External APIs
│   ├── exchange_rate_service.py  (NBP)
│   ├── company_info_service.py   (yfinance)
│   └── service_factory.py
├── utils/               # Utilities
│   ├── date_utils.py
│   ├── env_config.py
│   ├── logging_config.py
│   └── exceptions.py
├── data/                # Input CSV files (gitignored)
├── output/              # Generated reports (gitignored)
├── main.py              # CLI entry point
├── pyproject.toml       # Project metadata
└── README.md
```

### Extending the Application

**Add a new transaction type:**
1. Create subclass in `models/transaction.py`
2. Update `Trading212Parser.ACTION_TO_TYPE`
3. Create calculator implementing `CalculatorInterface`
4. Update `TaxFormGenerator` to include new data
5. Update exporters to display new calculations

**Add support for another broker:**
1. Implement new parser extending `ParserInterface`
2. Map broker's CSV format to `Transaction` models
3. Ensure date/currency/fee handling is correct

**Add new export format (e.g., JSON):**
1. Implement `ExporterInterface`
2. Convert `TaxFormData` to desired format
3. Register in `main.py`

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_fifo_calculator.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

## Troubleshooting

### PDF Shows Boxes Instead of Polish Characters

**Problem**: PDF displays � or boxes instead of ą, ć, ę, etc.

**Solution**: Install Unicode-compatible fonts:
```bash
# macOS
brew install --cask font-dejavu

# Ubuntu/Debian
sudo apt-get install fonts-dejavu

# Fedora
sudo dnf install dejavu-sans-fonts
```

The application will automatically detect and use the best available font.

### "No Exchange Rate Found" Error

**Problem**: NBP API cannot find exchange rate for a date

**Solution**: This usually happens for:
- Weekends (NBP doesn't publish rates)
- Public holidays
- Very old dates

The application automatically retries up to 7 previous business days. If this fails, check your internet connection or the transaction date.

### Dividends Not Appearing in Report

**Problem**: You have dividends in CSV but they don't show in the report

**Possible causes**:
1. Dividend has quantity = 0 (check CSV)
2. Missing ISIN or company name (required for country lookup)
3. Transaction date is outside selected tax year

Check the log file (`logs/trading212_tax_calculator.log`) for validation warnings.

### Wrong Country for Dividends

**Problem**: Calculator shows wrong country for a stock

**Solution**: The application uses:
1. yfinance API to determine company country
2. ISIN prefix as fallback (first 2 characters)

If incorrect, this is likely a yfinance data issue. You can manually edit the processed CSV before running calculation mode.

## FAQ

**Q: Can I use this for other brokers?**
A: Currently only Trading212 CSV format is supported. You'd need to implement a new parser for other brokers.

**Q: What if I have transactions in multiple years?**
A: Use the `-y YEAR` flag to calculate specific years separately, or omit it to process all years at once.

**Q: Do I need to pay tax on unrealized gains?**
A: No. The calculator only processes realized gains (actual sales). Unrealized gains (holdings you haven't sold) are not taxed.

**Q: How accurate are the calculations?**
A: The calculator follows Polish tax law and uses official NBP rates. However, always verify with a tax advisor for your specific situation.

**Q: What about wash sales or other advanced tax rules?**
A: Currently not implemented. The calculator uses simple FIFO matching.

**Q: Can I deduct trading losses?**
A: Yes, losses from stock sales reduce your taxable profit automatically. See PIT-38 field C.27 (loss).

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows SOLID principles
- New features have appropriate tests
- Documentation is updated
- Polish tax law compliance is maintained

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributors

- [R4Sput1n](https://github.com/R4Sput1n) - Initial work
- [Claude Sonnet 4.5](https://anthropic.com/claude) - Code refactoring, architecture design, and feature enhancements

## Acknowledgments

- [Artur Wiśniewski](https://stockbroker.pl/author/archislaw-makler/) for his comprehensive [guide on ETF tax calculations in Poland](https://stockbroker.pl/etf-jak-rozliczac-podatki-przewodnik-krok-po-kroku/)
- Polish Ministry of Finance for maintaining the [list of tax treaties](https://www.podatki.gov.pl/)
- [NBP (Narodowy Bank Polski)](https://nbp.pl/) for providing free exchange rate API

## Support

If you find this tool helpful, please:
- ⭐ Star the repository
- 🐛 Report bugs via [GitHub Issues](https://github.com/R4Sput1n/trading212-tax-calculator-PL/issues)
- 📖 Improve documentation
- 🔀 Submit pull requests

---

**Made with ❤️ for Polish investors using Trading212**

