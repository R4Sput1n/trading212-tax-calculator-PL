# Trading212 Tax Calculator 🇵🇱

A modular, object-oriented tool for calculating taxes for Trading212 transactions in Poland.

## Overview

This application processes CSV files exported from Trading212 and calculates tax data for Polish tax forms **PIT-38** and **PIT/ZG**. It handles stock transactions (using FIFO method), dividends (including foreign tax credits), and interest income.

> **⚠️ DISCLAIMER**: I am not a tax advisor. The Polish tax system can be overwhelming at times, and this tool is provided as-is without any warranty. For any tax advice or detailed information, please contact your local tax advisor or Krajową Informację Skarbową ([contact form](https://www.podatki.gov.pl/skontaktuj-sie-z-nami/pytanie-e-mail/masz-pytanie/)).

---

## 📋 Table of Contents

- [Features](#features)
- [Understanding Polish Tax on Investments](#understanding-polish-tax-on-investments)
  - [PIT-38 Form](#pit-38-form)
  - [PIT/ZG Attachment](#pitzg-attachment)
  - [FIFO Method Explained](#fifo-method-explained)
  - [Exchange Rate Rules](#exchange-rate-rules)
  - [Dividend Taxation](#dividend-taxation)
  - [Interest on Cash](#interest-on-cash)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- ✅ Parsing Trading212 CSV export files
- ✅ Calculating stock sales using **FIFO** (First In, First Out) method
- ✅ Processing dividends and withholding taxes
- ✅ Converting foreign currencies to PLN using **NBP exchange rates**
- ✅ Generating tax data for **PIT-38** and **PIT/ZG** forms
- ✅ Exporting to **Excel** and **PDF** formats
- ✅ Full **Polish character support** in PDF reports
- ✅ Custom font support for PDF generation
- ✅ Filtering calculations by tax year

---

## Understanding Polish Tax on Investments

### PIT-38 Form

**PIT-38** is the Polish tax form for reporting income from capital gains. You must file this form if you:

- Sold securities (stocks, ETFs, bonds)
- Received dividends from foreign companies
- Earned interest from foreign sources

**Key information:**
- 📅 **Filing deadline**: April 30th of the following year
- 💰 **Tax rate**: 19% flat tax on capital gains
- 📊 **Sections**: 
  - Section C: Securities income/costs
  - Section G: Foreign dividends

### PIT/ZG Attachment

**PIT/ZG** is an attachment to PIT-38 for reporting foreign income. You need this if:

- Your securities are from foreign exchanges (US, UK, DE, etc.)
- You received dividends from foreign companies

Each country requires a **separate PIT/ZG attachment**.

### FIFO Method Explained

Poland requires the **FIFO (First In, First Out)** method for calculating capital gains on securities.

#### What is FIFO?

When you sell shares, FIFO matches the sale with your **oldest purchases first**. This determines your cost basis and profit/loss.

#### Step-by-Step Example

```
📊 Your Transactions:
┌─────────────────────────────────────────────────────┐
│ Buy  100 shares @ $10 each    (March 2024)          │
│ Buy   50 shares @ $15 each    (June 2024)           │
│ Buy   30 shares @ $12 each    (September 2024)      │
│ Sell 120 shares @ $20 each    (January 2025)        │
└─────────────────────────────────────────────────────┘

📈 FIFO Matching:
┌─────────────────────────────────────────────────────┐
│ Step 1: Match oldest buy (March) first              │
│   → 100 shares: Buy $10 → Sell $20                  │
│   → Profit: ($20 - $10) × 100 = $1,000              │
├─────────────────────────────────────────────────────┤
│ Step 2: Need 20 more shares, use next buy (June)    │
│   → 20 shares: Buy $15 → Sell $20                   │
│   → Profit: ($20 - $15) × 20 = $100                 │
├─────────────────────────────────────────────────────┤
│ Total Profit: $1,000 + $100 = $1,100                │
│ Tax Due (19%): $1,100 × 0.19 = $209                 │ 
└─────────────────────────────────────────────────────┘

📦 Remaining Portfolio:
┌─────────────────────────────────────────────────────┐
│ 30 shares @ $15 (remaining from June buy)           │
│ 30 shares @ $12 (September buy - untouched)         │
└─────────────────────────────────────────────────────┘
```

#### Visual Diagram

```
Buy #1 (Mar) ════════════════════════════════╗
100 @ $10                                    ║
                                             ╠══> Sell 120 @ $20
Buy #2 (Jun) ═══════════════════╗            ║    (Jan 2025)
50 @ $15        ║               ║════════════╝
                ║               ║
                ║ 20 shares ════╝
                ║
                ╚═══> 30 shares remain

Buy #3 (Sep) ═══════════════════════════════> 30 shares remain
30 @ $12
```

### Exchange Rate Rules

Polish tax law requires converting foreign currency transactions to PLN using **NBP (National Bank of Poland)** rates.

#### Key Rules:

1. **Rate Date**: Use the exchange rate from the **business day BEFORE** the transaction date
2. **Source**: Average mid-rate from NBP Table A
3. **Weekend/Holiday**: If the day before is a weekend or holiday, use the last available rate

#### Example:

```
Transaction: January 15, 2025 (Wednesday)
→ Use NBP rate from: January 14, 2025 (Tuesday)

Transaction: January 13, 2025 (Monday)
→ Use NBP rate from: January 10, 2025 (Friday)
  (Saturday and Sunday are not business days)
```

#### GBX (British Pence) Special Case:

Trading212 quotes some UK stocks in GBX (pence) rather than GBP (pounds):
- The calculator automatically converts GBX to GBP (divide by 100)
- Then converts GBP to PLN using the NBP rate

### Dividend Taxation

Foreign dividends are subject to both foreign withholding tax and Polish tax, but you can claim a **tax credit** to avoid double taxation.

#### How It Works:

```
📊 Dividend Taxation Example (US Stock):
┌─────────────────────────────────────────────────────┐
│ Gross Dividend Received:          $100.00           │
│ US Withholding Tax (15%):         - $15.00          │
│ Net Dividend Received:            $85.00            │
├─────────────────────────────────────────────────────┤
│ Convert to PLN (rate 4.0):        400.00 PLN        │
│ Tax Paid Abroad in PLN:           60.00 PLN         │
├─────────────────────────────────────────────────────┤
│ Polish Tax Due (19%):             76.00 PLN         │
│ Tax Credit (paid abroad):         - 60.00 PLN       │
│ Tax to Pay in Poland:             16.00 PLN         │
└─────────────────────────────────────────────────────┘
```

#### Formula:

```
Tax_to_pay_PL = max(0, Dividend_PLN × 19% - Tax_paid_abroad_PLN)
```

#### Common Withholding Tax Rates:

| Country | Standard Rate | With W-8BEN |
|---------|--------------|-------------|
| 🇺🇸 USA | 30% | 15% |
| 🇬🇧 UK | 0% | 0% |
| 🇩🇪 Germany | 26.375% | 15% |
| 🇮🇪 Ireland | 25% | 15% |
| 🇳🇱 Netherlands | 15% | 15% |

> **Tip**: Always submit a **W-8BEN** form to your broker to reduce US withholding tax from 30% to 15%. Trading212 does this automatically when you create account

### Interest on Cash

Trading212 pays interest on uninvested cash balances. This interest is taxable in Poland.

#### Tax Treatment:

- **Tax rate**: 19% flat tax
- **Form**: Reported in PIT-38
- **Currency conversion**: Same NBP rules as other transactions

---

## Installation

### Requirements

- Python 3.9+
- Required packages: pandas, openpyxl, requests, yfinance, python-dateutil, python-dotenv, reportlab

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/R4Sput1n/trading212-tax-calculator-PL.git
   cd trading212-tax-calculator-PL
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   # or
   pip install pandas openpyxl requests yfinance python-dateutil python-dotenv reportlab
   ```

4. **Configure personal data (optional):**
   Create a `.env` file with your information:
   ```env
   FULLNAME=Jan Kowalski
   PESEL=12345678901
   ADDRESS=ul. Przykładowa 123
   CITY=Warszawa
   POSTAL_CODE=00-001
   TAX_OFFICE=Urząd Skarbowy Warszawa-Śródmieście
   ```

---

## Usage

### Basic Commands

#### 1. All-in-one mode (recommended):
```bash
python main.py -m all -i /path/to/trading212/*.csv -y 2024
```

#### 2. Processing mode only:
```bash
python main.py -m processing -i /path/to/trading212/*.csv -o data/processed.csv
```

#### 3. Calculation mode only:
```bash
python main.py -m calculation -i data/processed.csv -r output/report.xlsx -y 2024
```

### Command Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--mode` | `-m` | Operating mode: `processing`, `calculation`, or `all` |
| `--input` | `-i` | Input file(s) or glob pattern |
| `--output` | `-o` | Output processed data file |
| `--report` | `-r` | Tax report output path |
| `--year` | `-y` | Tax year to calculate |
| `--verbose` | `-v` | Enable verbose logging |
| `--env-file` | | Path to .env file for personal data |
| `--font-path` | | Custom TTF font path for PDF |
| `--font-name` | | Name for custom font |

### Custom Font for PDF Reports

To use a custom font (e.g., Fira Code Nerd Font) for PDF reports:

```bash
python main.py -m all -i data/*.csv -y 2024 \
    --font-path "/path/to/FiraCodeNerdFont-Regular.ttf" \
    --font-name "FiraCode"
```

### Example Workflow

```bash
# 1. Export your Trading212 history as CSV
# 2. Run the calculator
python main.py -m all -i ~/Downloads/trading212-2024.csv -y 2024 -v

# 3. Review outputs:
#    - output/tax_report_2024.xlsx  (Excel with PIT-38/PIT-ZG data)
#    - output/tax_report_2024.pdf   (Detailed PDF report)
```

---

## Architecture

### Application Flow

```
┌─────────────────┐
│ Trading212 CSV  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Trading212      │────▶│ NBP Exchange    │
│ Parser          │     │ Rate Service    │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Transaction     │
│ Classification  │
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
┌───────┐ ┌───────┐ ┌─────────┐
│ FIFO  │ │Divid- │ │Interest │
│ Calc  │ │end    │ │ Calc    │
└───┬───┘ └───┬───┘ └────┬────┘
    │         │          │
    └────┬────┴──────────┘
         ▼
┌─────────────────┐
│ Tax Form        │
│ Generator       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ Excel │ │  PDF  │
│Report │ │Report │
└───────┘ └───────┘
```

### Project Structure

```
trading212-tax-calculator/
├── calculators/           # Tax calculation logic
│   ├── fifo_calculator.py
│   ├── dividend_calculator.py
│   └── interest_calculator.py
├── config/                # Application settings
├── exporters/             # Report generators
│   ├── reportlab_exporter.py  # PDF with Polish chars
│   └── tax_form_exporter.py   # Excel export
├── models/                # Data models
│   ├── transaction.py
│   └── portfolio.py
├── parsers/               # CSV parsers
│   └── trading212_parser.py
├── services/              # External APIs
│   ├── exchange_rate_service.py  # NBP rates
│   ├── company_info_service.py   # Country lookup
│   └── isin_service.py
├── utils/                 # Utilities
├── docs/                  # Documentation & diagrams
└── main.py               # Entry point
```

### Design Principles

The application follows **SOLID** principles:

- **S**ingle Responsibility: Each class has one job
- **O**pen/Closed: Extend via new classes, not modifications
- **L**iskov Substitution: Services are interchangeable
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: High-level depends on abstractions

---

## Troubleshooting

### Common Issues

#### 1. Polish characters display as "?" or boxes in PDF

**Cause**: DejaVu fonts not installed.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-dejavu-core

# Fedora
sudo dnf install dejavu-sans-fonts

# macOS (use Homebrew)
brew install font-dejavu
```

Or use a custom font:
```bash
python main.py -m all -i data/*.csv \
    --font-path "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" \
    --font-name "DejaVuSans"
```

#### 2. Exchange rate not found

**Cause**: NBP API might be temporarily unavailable or the date is too old.

**Solution**: 
- The calculator automatically tries up to 7 previous business days
- For very old transactions, rates might not be available via API

#### 3. Country shows "(from ISIN)"

**Cause**: yfinance couldn't determine the company's country, so it was derived from the ISIN code prefix.

**Solution**: 
- This is usually correct but verify manually for important transactions
- The first two letters of ISIN indicate the country of registration

#### 4. "No transactions found for year X"

**Cause**: No sales were made in that tax year.

**Note**: You only report sales in PIT-38, not purchases. If you only bought (no sales), there's nothing to report for securities.

### Getting Help

- 📖 [NBP Exchange Rates](https://www.nbp.pl/homen.aspx?f=/kursy/kursyen.htm)
- 📋 [PIT-38 Form Instructions](https://www.podatki.gov.pl/pit/formularze-do-druku-pit/)
- 💬 [Open an Issue](https://github.com/R4Sput1n/trading212-tax-calculator-PL/issues)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributors

- [R4Sput1n](https://github.com/R4Sput1n) - Initial work
- [Claude](https://anthropic.com/claude) - Code refactoring, modularization, and documentation

## Acknowledgments

- [Artur Wiśniewski](https://stockbroker.pl/author/archislaw-makler/) for his [guide on ETF tax calculations in Poland](https://stockbroker.pl/etf-jak-rozliczac-podatki-przewodnik-krok-po-kroku/)
- [NBP](https://www.nbp.pl/) for providing the exchange rate API
