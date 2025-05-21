import os
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from exporters.exporter_interface import ExporterInterface
from calculators.fifo_calculator import FifoCalculationResult
from calculators.dividend_calculator import DividendCalculationResult

logger = logging.getLogger(__name__)

class ReportLabExporter(ExporterInterface[Dict[str, Any]]):
    """Exporter for tax calculation results to PDF report using ReportLab"""

    def __init__(self, personal_data: Optional[Dict[str, str]] = None):
        """
        Initialize ReportLabExporter.

        Args:
            personal_data: Dictionary containing personal information for the report
        """
        self.personal_data = personal_data or {}
        self.logger = logging.getLogger(__name__)

        # Register fonts for Polish characters
        self._register_fonts()

        # Create styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _register_fonts(self):
        """Register fonts for Polish characters"""
        # Try to register Windows fonts for Polish characters
        try:
            # Import required modules
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Find Windows font directory (will be None on non-Windows systems)
            windows_font_dir = os.environ.get('WINDIR')
            if windows_font_dir:
                windows_font_dir = os.path.join(windows_font_dir, 'Fonts')

                # Define font files with full paths
                arial_path = os.path.join(windows_font_dir, 'arial.ttf')
                arial_bold_path = os.path.join(windows_font_dir, 'arialbd.ttf')
                times_path = os.path.join(windows_font_dir, 'times.ttf')
                calibri_path = os.path.join(windows_font_dir, 'calibri.ttf')

                # Try Arial first
                if os.path.exists(arial_path):
                    pdfmetrics.registerFont(TTFont('Arial', arial_path))

                    if os.path.exists(arial_bold_path):
                        pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
                        self.base_font_name = 'Arial'
                        self.bold_font_name = 'Arial-Bold'
                        self.logger.info(f"Using Arial fonts from {windows_font_dir}")
                        return
                    else:
                        # If bold Arial not available, use regular for both
                        self.base_font_name = 'Arial'
                        self.bold_font_name = 'Arial'
                        self.logger.info(f"Using Arial font (no bold) from {windows_font_dir}")
                        return

                # Try Times if Arial not available
                elif os.path.exists(times_path):
                    pdfmetrics.registerFont(TTFont('Times-Custom', times_path))
                    self.base_font_name = 'Times-Custom'
                    self.bold_font_name = 'Times-Custom'
                    self.logger.info(f"Using Times fonts from {windows_font_dir}")
                    return

                # Try Calibri if Times not available
                elif os.path.exists(calibri_path):
                    pdfmetrics.registerFont(TTFont('Calibri', calibri_path))
                    self.base_font_name = 'Calibri'
                    self.bold_font_name = 'Calibri'
                    self.logger.info(f"Using Calibri fonts from {windows_font_dir}")
                    return

            # Log which fonts were registered
            self.logger.info(f"Registered fonts: {list(pdfmetrics.getRegisteredFontNames())}")

        except Exception as e:
            self.logger.error(f"Error registering fonts: {e}")

        # If no custom fonts registered, fall back to default
        self.base_font_name = 'Helvetica'
        self.bold_font_name = 'Helvetica-Bold'
        self.logger.warning("No custom fonts registered, using Helvetica (Polish characters may not display correctly)")

    def _create_custom_styles(self):
        """Create custom paragraph and table styles"""
        # Use unique style names to avoid conflicts
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontName=self.bold_font_name,
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        ))

        self.styles.add(ParagraphStyle(
            name='ReportChapter',
            parent=self.styles['Heading1'],
            fontName=self.bold_font_name,
            fontSize=14,
            alignment=TA_LEFT,
            spaceAfter=10
        ))

        self.styles.add(ParagraphStyle(
            name='ReportSection',
            parent=self.styles['Heading2'],
            fontName=self.bold_font_name,
            fontSize=12,
            alignment=TA_LEFT,
            spaceAfter=8
        ))

        self.styles.add(ParagraphStyle(
            name='ReportBodyText',
            parent=self.styles['Normal'],
            fontName=self.base_font_name,
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
            encoding='utf-8'
        ))

        # Add a new cell style for wrapped header text
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontName=self.bold_font_name,
            fontSize=8,
            alignment=TA_CENTER,
            leading=10,  # Slightly increased leading for wrapped text
            spaceAfter=0,
            spaceBefore=0,
            encoding='utf-8'
        ))

        # Table header style - updated for better text wrapping
        self.table_header_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),  # Added top padding for header cells
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # Vertical alignment for headers
        ])

        # Table data style
        self.table_data_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Align ticker/name columns left
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ])

        # Summary table style
        self.summary_table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ])

    # Helper function to create paragraph-wrapped cells for table headers
    def _create_wrapped_header_cell(self, text):
        """Create a Paragraph object with wrapping for table headers"""
        return Paragraph(text, self.styles['TableHeader'])

    def format_decimal(self, value: Decimal, decimals: int = 2) -> str:
        """
        Format a decimal value with Polish formatting (comma as decimal separator).
        Preserves more decimal places for certain values.

        Args:
            value: Decimal value to format
            decimals: Number of decimal places (default is 2, but will be increased for small values)

        Returns:
            Formatted value as string
        """
        # Handle None or zero values
        if value is None:
            return "0,00"

        if isinstance(value, str):
            try:
                value = Decimal(value.replace(',', '.'))
            except:
                return value

        # Determine appropriate decimal places based on the value
        if abs(value) < 1 and value != 0:
            # For small values like exchange rates, show more decimal places
            actual_decimals = max(5, decimals)
        elif value == int(value):
            # For whole numbers, show no decimals
            actual_decimals = 0
        else:
            # Default decimal places
            actual_decimals = decimals

        # Format with comma as decimal separator (Polish style)
        formatted = str(round(float(value), actual_decimals)).replace('.', ',')

        # Add trailing zeros if needed
        if ',' in formatted:
            integer_part, decimal_part = formatted.split(',')
            # Don't add trailing zeros if we're using variable precision
            if abs(value) < 1 and value != 0:
                pass
            else:
                decimal_part = decimal_part.ljust(actual_decimals, '0')
            formatted = f"{integer_part},{decimal_part}"
        elif actual_decimals > 0:
            formatted = f"{formatted},{('0' * actual_decimals)}"

        return formatted

    def format_date(self, date) -> str:
        """
        Format date in Polish format (DD.MM.YYYY).

        Args:
            date: Date to format

        Returns:
            Formatted date as string
        """
        if isinstance(date, str):
            try:
                date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return date

        if isinstance(date, datetime):
            return date.strftime("%d.%m.%Y")

        return str(date)

    def format_currency(self, value: Decimal) -> str:
        """
        Format a currency value with Polish formatting (comma as decimal separator).
        Always shows 2 decimal places for currency.

        Args:
            value: Decimal value to format

        Returns:
            Formatted value as string
        """
        if value is None:
            return "0,00"

        # Always use 2 decimal places for currency
        formatted = str(round(float(value), 2)).replace('.', ',')

        # Add trailing zeros if needed
        if ',' in formatted:
            integer_part, decimal_part = formatted.split(',')
            decimal_part = decimal_part.ljust(2, '0')
            formatted = f"{integer_part},{decimal_part}"
        else:
            formatted = f"{formatted},00"

        return formatted

    def create_title_page(self, tax_year: Optional[int] = None) -> List[Any]:
        """
        Create title page elements.

        Args:
            tax_year: Tax year for the report

        Returns:
            List of flowable elements
        """
        elements = []

        # Title
        elements.append(Spacer(1, 2 * cm))
        elements.append(Paragraph("Szczegółowy raport podatkowy - Trading212", self.styles['ReportTitle']))
        elements.append(Spacer(1, 0.5 * cm))

        # Subtitle
        subtitle = "Rozliczenie sprzedaży akcji i dywidend"
        if tax_year:
            subtitle += f" {tax_year}"
        elements.append(Paragraph(subtitle, self.styles['ReportTitle']))

        elements.append(Spacer(1, 2 * cm))

        # Personal data
        fullname = self.personal_data.get('FULLNAME', 'UZUPEŁNIJ IMIĘ I NAZWISKO')
        pesel = self.personal_data.get('PESEL', 'UZUPEŁNIJ PESEL')
        address = self.personal_data.get('ADDRESS', 'UZUPEŁNIJ ADRES')
        city = self.personal_data.get('CITY', 'UZUPEŁNIJ MIASTO')
        postal_code = self.personal_data.get('POSTAL_CODE', 'UZUPEŁNIJ KOD POCZTOWY')
        tax_office = self.personal_data.get('TAX_OFFICE', 'UZUPEŁNIJ URZĄD SKARBOWY')

        personal_data = [
            ["Imię i nazwisko:", fullname],
            ["PESEL:", pesel],
            ["Adres:", address],
            ["", f"{postal_code} {city}"],
            ["Urząd skarbowy:", tax_office]
        ]

        # Create table for personal data
        personal_table = Table(personal_data, colWidths=[4 * cm, 10 * cm])
        personal_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(personal_table)

        elements.append(Spacer(1, 2 * cm))

        # Tax year
        year_text = f"Rok podatkowy: {tax_year}" if tax_year else "Rok podatkowy: Wszystkie lata"
        elements.append(Paragraph(year_text, self.styles['ReportBodyText']))

        elements.append(Spacer(1, 4 * cm))

        # Footer
        elements.append(Paragraph("Dokument wygenerowany automatycznie przez program Trading212 Tax Calculator",
                                  self.styles['ReportBodyText']))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Wersja: 1.0.0", self.styles['ReportBodyText']))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(
            "Ten raport zawiera szczegółowe obliczenia podatkowe na podstawie historii transakcji z platformy Trading212.",
            self.styles['ReportBodyText']))

        elements.append(PageBreak())

        return elements

    def create_fifo_section(self, fifo_result: FifoCalculationResult) -> List[Any]:
        """
        Create FIFO section elements.

        Args:
            fifo_result: Result of FIFO calculation

        Returns:
            List of flowable elements
        """
        elements = []

        # Chapter title
        elements.append(Paragraph("1. Rozliczenie transakcji - metoda FIFO", self.styles['ReportChapter']))
        elements.append(
            Paragraph("Poniżej przedstawiono rozliczenie transakcji sprzedaży akcji metodą FIFO (First In, First Out).",
                      self.styles['ReportBodyText']))

        # FIFO formula
        elements.append(Paragraph("1.1 Wzór obliczeń metodą FIFO", self.styles['ReportSection']))
        elements.append(Paragraph(
            "Metoda FIFO (First In, First Out) polega na przyporządkowaniu sprzedanych akcji do najwcześniej zakupionych akcji. "
            "Dla każdej transakcji sprzedaży obowiązuje następujący wzór:",
            self.styles['ReportBodyText']
        ))

        formula_text = [
            "P = S - K",
            "",
            "gdzie:",
            "P = Dochód/strata ze sprzedaży",
            "S = Przychód ze sprzedaży (cena sprzedaży × liczba akcji)",
            "K = Koszt uzyskania przychodu (cena zakupu × liczba akcji + opłaty)"
        ]

        formula_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

        formula_table = Table([[p] for p in formula_text], colWidths=[15 * cm])
        formula_table.setStyle(formula_style)
        elements.append(formula_table)

        elements.append(Paragraph(
            "Przychód oraz koszt zawsze przeliczane są na PLN według kursu NBP z dnia poprzedzającego dzień transakcji.",
            self.styles['ReportBodyText']
        ))

        # Buy transactions
        buy_transactions = {}
        for match in fifo_result.matches:
            buy_key = (match.buy_transaction.ticker, match.buy_date)
            if buy_key not in buy_transactions:
                buy_transactions[buy_key] = match.buy_transaction

        if buy_transactions:
            elements.append(Paragraph("1.2 Transakcje zakupu", self.styles['ReportSection']))

            # Table header - use Paragraph objects for wrapping text in headers
            buy_header = [
                self._create_wrapped_header_cell("Data"),
                self._create_wrapped_header_cell("Ticker"),
                self._create_wrapped_header_cell("Nazwa"),
                self._create_wrapped_header_cell("Ilość"),
                self._create_wrapped_header_cell("Cena"),
                self._create_wrapped_header_cell("Waluta"),
                self._create_wrapped_header_cell("Kurs NBP"),
                self._create_wrapped_header_cell("Wartość w walucie"),
                self._create_wrapped_header_cell("Wartość w PLN"),
                self._create_wrapped_header_cell("Opłaty w PLN")
            ]

            # Calculate column widths based on content
            col_widths = [
                2.0 * cm,  # Data
                1.5 * cm,  # Ticker
                3.5 * cm,  # Nazwa
                1.2 * cm,  # Ilość
                1.5 * cm,  # Cena
                1.5 * cm,  # Waluta
                1.5 * cm,  # Kurs NBP
                2.0 * cm,  # Wartość w walucie
                2.0 * cm,  # Wartość w PLN
                1.8 * cm,  # Opłaty w PLN
            ]

            # Table data
            buy_data = [buy_header]
            for (ticker, date), tx in sorted(buy_transactions.items(), key=lambda x: x[0][1]):
                # Format exchange rate based on currency
                if tx.currency == 'GBX':
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate, decimals=5)
                else:
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate)

                buy_data.append([
                    self.format_date(date),
                    ticker,
                    tx.name[:20],
                    self.format_decimal(tx.quantity),
                    self.format_decimal(tx.price_per_share, decimals=2),
                    tx.currency,
                    exchange_rate_formatted,
                    self.format_currency(tx.total_value_foreign),
                    self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal('0'))
                ])

                # Create table with updated style for wrapped headers
            buy_table = Table(buy_data, colWidths=col_widths, repeatRows=1)
            buy_table_style = TableStyle([
                # Header style with updated padding and alignment for wrapped text
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                # Data style
                ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Align name column left
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ])
            buy_table.setStyle(buy_table_style)

            elements.append(buy_table)
        else:
            elements.append(Paragraph("1.2 Transakcje zakupu", self.styles['ReportSection']))
            elements.append(Paragraph("Brak transakcji zakupu.", self.styles['ReportBodyText']))

        # Sell transactions
        sell_transactions = {}
        for match in fifo_result.matches:
            sell_key = (match.sell_transaction.ticker, match.sell_date)
            if sell_key not in sell_transactions:
                sell_transactions[sell_key] = match.sell_transaction

        if sell_transactions:
            elements.append(Paragraph("1.3 Transakcje sprzedaży", self.styles['ReportSection']))

            # Table header with wrapped text in Paragraph objects
            sell_header = [
                self._create_wrapped_header_cell("Data"),
                self._create_wrapped_header_cell("Ticker"),
                self._create_wrapped_header_cell("Nazwa"),
                self._create_wrapped_header_cell("Ilość"),
                self._create_wrapped_header_cell("Cena"),
                self._create_wrapped_header_cell("Waluta"),
                self._create_wrapped_header_cell("Kurs NBP"),
                self._create_wrapped_header_cell("Wartość w walucie"),
                self._create_wrapped_header_cell("Wartość w PLN"),
                self._create_wrapped_header_cell("Opłaty w PLN")
            ]

            # Table data
            sell_data = [sell_header]

            for (ticker, date), tx in sorted(sell_transactions.items(), key=lambda x: x[0][1]):
                # Format exchange rate based on currency
                if tx.currency == 'GBX':
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate, decimals=5)
                else:
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate)

                sell_data.append([
                    self.format_date(date),
                    ticker,
                    tx.name[:20],
                    self.format_decimal(tx.quantity),
                    self.format_decimal(tx.price_per_share, decimals=2),
                    tx.currency,
                    exchange_rate_formatted,
                    self.format_currency(tx.total_value_foreign),
                    self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal('0'))
                ])

            # Create table
            sell_table = Table(sell_data, colWidths=col_widths, repeatRows=1)
            sell_table.setStyle(buy_table_style)  # Reuse the same style

            elements.append(sell_table)
        else:
            elements.append(Paragraph("1.3 Transakcje sprzedaży", self.styles['ReportSection']))
            elements.append(Paragraph("Brak transakcji sprzedaży.", self.styles['ReportBodyText']))

        # FIFO matches
        if fifo_result.matches:
            elements.append(Paragraph("1.4 Rozliczenie transakcji metodą FIFO", self.styles['ReportSection']))

            # Table header with wrapped text
            matches_header = [
                self._create_wrapped_header_cell("Ticker"),
                self._create_wrapped_header_cell("Data zakupu"),
                self._create_wrapped_header_cell("Data sprzedaży"),
                self._create_wrapped_header_cell("Liczba akcji"),
                self._create_wrapped_header_cell("Przychód (PLN)"),
                self._create_wrapped_header_cell("Koszt (PLN)"),
                self._create_wrapped_header_cell("Dochód/Strata (PLN)"),
                self._create_wrapped_header_cell("% zysku/straty"),
                self._create_wrapped_header_cell("Kraj")
            ]

            # Calculate column widths for matches table
            match_col_widths = [
                1.5 * cm,  # Ticker
                2.0 * cm,  # Data zakupu
                2.0 * cm,  # Data sprzedaży
                1.5 * cm,  # Liczba akcji
                2.0 * cm,  # Przychód (PLN)
                2.0 * cm,  # Koszt (PLN)
                2.0 * cm,  # Dochód/Strata (PLN)
                2.0 * cm,  # % zysku/straty
                3.0 * cm,  # Kraj
            ]

            # Table data
            matches_data = [matches_header]

            for match in sorted(fifo_result.matches, key=lambda m: (m.sell_date, m.ticker)):
                profit_percent = (match.profit_loss_pln / match.cost_pln) * 100 if match.cost_pln > 0 else 0
                matches_data.append([
                    match.ticker,
                    self.format_date(match.buy_date),
                    self.format_date(match.sell_date),
                    self.format_decimal(match.used_quantity),
                    self.format_currency(match.income_pln),
                    self.format_currency(match.cost_pln),
                    self.format_currency(match.profit_loss_pln),
                    f"{self.format_decimal(profit_percent, decimals=2)}%",
                    match.country
                ])

            # Create table
            matches_table = Table(matches_data, colWidths=match_col_widths, repeatRows=1)
            matches_table.setStyle(buy_table_style)  # Reuse the same style

            elements.append(matches_table)
        else:
            elements.append(Paragraph("1.4 Rozliczenie transakcji metodą FIFO", self.styles['ReportSection']))
            elements.append(Paragraph("Brak transakcji do rozliczenia.", self.styles['ReportBodyText']))

        elements.extend(self.create_transaction_details_section(fifo_result))
        # FIFO summary
        elements.append(Paragraph("1.6 Podsumowanie rozliczenia metodą FIFO", self.styles['ReportSection']))

        # Calculate summary data
        total_income = sum(match.income_pln for match in fifo_result.matches)
        total_cost = sum(match.cost_pln for match in fifo_result.matches)
        total_profit = sum(match.profit_loss_pln for match in fifo_result.matches if match.profit_loss_pln > 0)
        total_loss = sum(abs(match.profit_loss_pln) for match in fifo_result.matches if match.profit_loss_pln < 0)
        tax_base = int(max(0, total_profit - total_loss))
        tax_due = int(tax_base * Decimal('0.19'))

        # Summary table data
        summary_data = [
            ["Pozycja", "Wartość (PLN)"],
            ["Łączny przychód", self.format_currency(total_income)],
            ["Łączny koszt uzyskania przychodu", self.format_currency(total_cost)],
            ["Łączny dochód", self.format_currency(total_profit)],
            ["Łączna strata", self.format_currency(total_loss)],
            ["Podstawa opodatkowania", str(tax_base)],
            ["Podatek należny (19%)", str(tax_due)]
        ]

        # Create summary table
        summary_table = Table(summary_data, colWidths=[10 * cm, 5 * cm])
        summary_table.setStyle(self.summary_table_style)

        elements.append(summary_table)

        elements.append(PageBreak())

        return elements

    def create_transaction_details_section(self, fifo_result: FifoCalculationResult) -> List[Any]:
        """
        Create a detailed section for each sell transaction.

        Args:
            fifo_result: Result of FIFO calculation

        Returns:
            List of flowable elements
        """
        elements = []

        # Section title (now as subsection of FIFO)
        elements.append(Paragraph("1.5 Szczegóły transakcji", self.styles['ReportSection']))
        elements.append(Paragraph(
            "Poniżej przedstawiono szczegółowe rozliczenie każdej transakcji sprzedaży z uwzględnieniem dopasowanych transakcji zakupu.",
            self.styles['ReportBodyText']))
        # Group matches by sell transaction
        sell_transactions = {}
        for match in fifo_result.matches:
            # Group by sell transaction (ticker and date combination)
            sell_key = (match.sell_transaction.ticker, match.sell_date)
            if sell_key not in sell_transactions:
                sell_transactions[sell_key] = []
            sell_transactions[sell_key].append(match)

        # Sort sell transactions by date and ticker
        sorted_sell_keys = sorted(sell_transactions.keys(), key=lambda x: (x[1], x[0]))

        # Add section for each sell transaction
        for section_idx, sell_key in enumerate(sorted_sell_keys, 1):
            ticker, sell_date = sell_key
            matches_for_this_sell = sell_transactions[sell_key]

            # Get the sell transaction from the first match (all matches in this group have the same sell transaction)
            # Get the first match just to reference the transaction details
            first_match = matches_for_this_sell[0]
            sell_tx = first_match.sell_transaction

            logger.info(f"Creating detailed section for {ticker} ({self.format_date(sell_date)})")
            logger.info(f"  Sell transaction total fees: {sell_tx.fees_pln}")
            logger.info(f"  Sell transaction currency conversion fee: {sell_tx.currency_conversion_fee_pln}")

            # Section title
            elements.append(Paragraph(f"1.5.{section_idx} Szczegóły dla {ticker} ({self.format_date(sell_date)})",
                                      self.styles['ReportBodyText']))
            # Create transaction details table (headers as rows for better readability)
            tx_details = [
                ["Ticker:", ticker],
                ["Nazwa:", sell_tx.name],
                ["Data sprzedaży:", self.format_date(sell_date)],
                ["Ilość sprzedanych akcji:", self.format_decimal(sell_tx.quantity)],
                ["Cena sprzedaży (za akcję):", f"{self.format_decimal(sell_tx.price_per_share)} {sell_tx.currency}"],
                ["Kurs NBP dla sprzedaży:", self.format_decimal(sell_tx.exchange_rate)],
                ["Wartość sprzedaży w walucie:",
                 f"{self.format_currency(sell_tx.total_value_foreign)} {sell_tx.currency}"],
                ["Wartość sprzedaży w PLN:", f"{self.format_currency(sell_tx.total_value_pln)} PLN"],
                ["Koszt przewalutowania przy sprzedaży:",
                 f"{self.format_currency(first_match.sell_currency_conversion_fee_pln)} PLN"]
            ]

            # Add spacer
            elements.append(Spacer(1, 0.3 * cm))

            # Create table
            tx_table = Table(tx_details, colWidths=[5 * cm, 10 * cm])
            tx_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), self.bold_font_name),
                ('FONTNAME', (1, 0), (1, -1), self.base_font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ]))

            elements.append(tx_table)

            # Add matched buy transactions
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph("Dopasowane transakcje zakupu:", self.styles['ReportBodyText']))

            # Calculation details for each matched buy transaction
            total_cost_pln = Decimal('0')
            total_income_pln = Decimal('0')

            for idx, buy_match in enumerate(sorted(matches_for_this_sell, key=lambda m: m.buy_date), 1):
                # Buy transaction
                buy_tx = buy_match.buy_transaction

                # Add debug logs
                logger.debug(f"  Match #{idx} for {ticker}:")
                logger.debug(f"    Buy currency conversion fee PLN: {buy_match.buy_currency_conversion_fee_pln}")

                # Create buy transaction details table
                buy_details = [
                    ["Transakcja zakupu #" + str(idx), ""],
                    ["Data zakupu:", self.format_date(buy_match.buy_date)],
                    ["Ilość dopasowanych akcji:", self.format_decimal(buy_match.used_quantity)],
                    ["Cena zakupu (za akcję):", f"{self.format_decimal(buy_tx.price_per_share)} {buy_tx.currency}"],
                    ["Kurs NBP dla zakupu:", self.format_decimal(buy_tx.exchange_rate)],
                    ["Wartość zakupu w walucie (dla dopasowanych akcji):",
                     f"{self.format_currency(buy_tx.price_per_share * buy_match.used_quantity)} {buy_tx.currency}"],
                    ["Wartość zakupu w PLN (dla dopasowanych akcji):",
                     f"{self.format_currency(buy_match.buy_price_pln)} PLN"],
                    ["Koszt przewalutowania przy kupnie:",
                     f"{self.format_currency(buy_match.buy_currency_conversion_fee_pln)} PLN"]
                ]

                # Create table
                buy_table = Table(buy_details, colWidths=[7 * cm, 8 * cm])
                buy_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), self.base_font_name),
                    ('FONTNAME', (1, 0), (1, -1), self.base_font_name),
                    ('FONTNAME', (0, 0), (1, 0), self.bold_font_name),  # Make header row bold
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('ALIGN', (0, 0), (1, 0), 'CENTER'),  # Center the header
                    ('SPAN', (0, 0), (1, 0)),  # Span the header across both columns
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
                    ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),  # Header background
                ]))

                elements.append(buy_table)
                elements.append(Spacer(1, 0.2 * cm))

                total_cost_pln += buy_match.cost_pln
                total_income_pln += buy_match.income_pln

            # Final calculation for this sell transaction
            profit_loss_pln = total_income_pln - total_cost_pln
            profit_percent = (profit_loss_pln / total_cost_pln * 100) if total_cost_pln > 0 else Decimal('0')

            elements.append(Spacer(1, 0.3 * cm))
            elements.append(Paragraph("Podsumowanie rozliczenia transakcji:", self.styles['ReportBodyText']))

            # Get the specific matches for this sell transaction
            matches_for_this_sell = sell_transactions[sell_key]

            # Calculate the summary data for just this transaction
            total_income_pln = sum(m.income_pln for m in matches_for_this_sell)
            total_cost_pln = sum(m.cost_pln for m in matches_for_this_sell)
            profit_loss_pln = total_income_pln - total_cost_pln
            profit_percent = (profit_loss_pln / total_cost_pln * 100) if total_cost_pln > 0 else Decimal('0')

            # Create the summary table
            summary_data = [
                ["Przychód (PLN):", self.format_currency(total_income_pln)],
                ["Koszt uzyskania przychodu (PLN):", self.format_currency(total_cost_pln)],
                ["Dochód / Strata (PLN):", self.format_currency(profit_loss_pln)],
                ["Procentowy zysk / strata:", f"{self.format_decimal(profit_percent, decimals=2)}%"],
            ]

            # Create summary table
            summary_table = Table(summary_data, colWidths=[7 * cm, 8 * cm])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), self.bold_font_name),
                ('FONTNAME', (1, 0), (1, -1), self.base_font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ]))

            elements.append(summary_table)

            # Add space between transactions
            elements.append(Spacer(1, 1 * cm))

            # Add page break after set number of transactions or for the last transaction
            if section_idx % 2 == 0 or section_idx == len(sorted_sell_keys):
                elements.append(PageBreak())

        return elements

    def create_dividend_section(self, dividend_result: DividendCalculationResult) -> List[Any]:
        """
        Create dividend section elements.

        Args:
            dividend_result: Result of dividend calculation

        Returns:
            List of flowable elements
        """
        elements = []

        # Chapter title
        elements.append(Paragraph("2. Rozliczenie dywidend", self.styles['ReportChapter']))
        elements.append(Paragraph(
            "Poniżej przedstawiono rozliczenie przychodów z dywidend z uwzględnieniem podatku zapłaconego za granicą.",
            self.styles['ReportBodyText']))

        if not dividend_result.summaries:
            elements.append(Paragraph("2.1 Brak dywidend", self.styles['ReportSection']))
            elements.append(Paragraph("Nie znaleziono żadnych dywidend do rozliczenia.", self.styles['ReportBodyText']))
            elements.append(PageBreak())
            return elements

        # Dividend formula
        elements.append(Paragraph("2.1 Wzór obliczeń dla dywidend", self.styles['ReportSection']))
        elements.append(Paragraph(
            "Przy dywidendach zagranicznych stosuje się następujący wzór na podatek do zapłaty w Polsce:",
            self.styles['ReportBodyText']
        ))

        formula_text = [
            "P_PL = max(0, P_należny - P_zagr)",
            "",
            "gdzie:",
            "P_PL = Podatek do zapłaty w Polsce",
            "P_należny = Podatek należny w Polsce (dywidenda × 19%)",
            "P_zagr = Podatek już zapłacony za granicą"
        ]

        formula_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

        formula_table = Table([[p] for p in formula_text], colWidths=[15 * cm])
        formula_table.setStyle(formula_style)
        elements.append(formula_table)

        elements.append(Paragraph(
            "Dywidendy zawsze przeliczane są na PLN według kursu NBP z dnia poprzedzającego dzień wypłaty dywidendy.",
            self.styles['ReportBodyText']
        ))

        # Create global summary table
        elements.append(Paragraph("2.2 Podsumowanie wszystkich dywidend", self.styles['ReportSection']))

        # Table header with wrapped text
        summary_header = [
            self._create_wrapped_header_cell("Państwo"),
            self._create_wrapped_header_cell("Dywidenda (PLN)"),
            self._create_wrapped_header_cell("Podatek pobrany (PLN)"),
            self._create_wrapped_header_cell("Podatek PL 19% (PLN)"),
            self._create_wrapped_header_cell("Do zapłaty w PL (PLN)")
        ]

        # Calculate column widths
        summary_col_widths = [
            4.0 * cm,  # Państwo
            3.5 * cm,  # Dywidenda (PLN)
            3.5 * cm,  # Podatek pobrany (PLN)
            3.5 * cm,  # Podatek PL 19% (PLN)
            3.5 * cm,  # Do zapłaty w PL (PLN)
        ]

        # Table data
        summary_data = [summary_header]
        total_dividend = Decimal('0')
        total_tax_abroad = Decimal('0')
        total_tax_poland = Decimal('0')
        total_tax_to_pay = Decimal('0')

        for country, summary in sorted(dividend_result.summaries.items()):
            summary_data.append([
                country,
                self.format_currency(summary.total_dividend_pln),
                self.format_currency(summary.tax_paid_abroad_pln),
                self.format_currency(summary.tax_due_poland),
                self.format_currency(summary.tax_to_pay)
            ])

            total_dividend += summary.total_dividend_pln
            total_tax_abroad += summary.tax_paid_abroad_pln
            total_tax_poland += summary.tax_due_poland
            total_tax_to_pay += summary.tax_to_pay

        # Add total row
        summary_data.append([
            "RAZEM",
            self.format_currency(total_dividend),
            self.format_currency(total_tax_abroad),
            self.format_currency(total_tax_poland),
            self.format_currency(total_tax_to_pay)
        ])

        # Create table
        summary_table = Table(summary_data, colWidths=summary_col_widths, repeatRows=1)
        summary_style = TableStyle([
            # Header style with improved padding and alignment for wrapped text
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

            # Data style
            ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

            # Total row style
            ('FONTNAME', (0, -1), (-1, -1), self.bold_font_name),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
        ])
        summary_table.setStyle(summary_style)

        elements.append(summary_table)

        # Create country sections
        for country_idx, (country, summary) in enumerate(sorted(dividend_result.summaries.items()), 1):
            elements.append(Paragraph(f"2.{country_idx + 2} Dywidendy - {country}", self.styles['ReportSection']))

            # Table header with wrapped text
            div_header = [
                self._create_wrapped_header_cell("Data"),
                self._create_wrapped_header_cell("Ticker"),
                self._create_wrapped_header_cell("Nazwa"),
                self._create_wrapped_header_cell("Ilość"),
                self._create_wrapped_header_cell("Dywidenda/akcję"),
                self._create_wrapped_header_cell("Waluta"),
                self._create_wrapped_header_cell("Kurs NBP"),
                self._create_wrapped_header_cell("Wartość w walucie"),
                self._create_wrapped_header_cell("Wartość w PLN"),
                self._create_wrapped_header_cell("Podatek pobrany"),
                self._create_wrapped_header_cell("Podatek w PLN")
            ]

            # Calculate column widths
            div_col_widths = [
                1.8 * cm,  # Data
                1.3 * cm,  # Ticker
                2.5 * cm,  # Nazwa
                1.0 * cm,  # Ilość
                1.7 * cm,  # Dywidenda/akcję
                1.2 * cm,  # Waluta
                1.5 * cm,  # Kurs NBP
                1.8 * cm,  # Wartość w walucie
                1.8 * cm,  # Wartość w PLN
                1.7 * cm,  # Podatek pobrany
                1.7 * cm,  # Podatek w PLN
            ]

            # Table data
            div_data = [div_header]

            for tx in sorted(summary.transactions, key=lambda t: t.date):
                # Format exchange rate based on currency
                if tx.currency == 'GBX':
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate, decimals=5)
                else:
                    exchange_rate_formatted = self.format_decimal(tx.exchange_rate)

                div_data.append([
                    self.format_date(tx.date),
                    tx.ticker,
                    tx.name[:20],
                    self.format_decimal(tx.quantity),
                    self.format_decimal(tx.price_per_share, decimals=4),
                    tx.currency,
                    exchange_rate_formatted,
                    self.format_currency(tx.total_value_foreign),
                    self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.withholding_tax_foreign or Decimal('0')),
                    self.format_currency(tx.withholding_tax_pln or Decimal('0'))
                ])

            # Create table
            div_table = Table(div_data, colWidths=div_col_widths, repeatRows=1)
            div_style = TableStyle([
                # Header style with improved padding and alignment for wrapped text
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                # Data style
                ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Align name column left
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ])
            div_table.setStyle(div_style)

            elements.append(div_table)

            # Create summary table for country
            elements.append(Paragraph("Podsumowanie", self.styles['ReportBodyText']))

            country_summary_data = [
                ["Pozycja", "Wartość (PLN)"],
                ["Suma dywidend", self.format_currency(summary.total_dividend_pln)],
                ["Podatek pobrany", self.format_currency(summary.tax_paid_abroad_pln)],
                ["Podatek PL (19%)", self.format_currency(summary.tax_due_poland)],
                ["Do zapłaty w PL", self.format_currency(summary.tax_to_pay)]
            ]

            country_summary_table = Table(country_summary_data, colWidths=[6 * cm, 3 * cm])
            country_summary_table.setStyle(self.summary_table_style)

            elements.append(country_summary_table)
            elements.append(Spacer(1, 0.5 * cm))

        elements.append(PageBreak())

        return elements

    def create_tax_forms_section(self, fifo_result: FifoCalculationResult,
                                 dividend_result: DividendCalculationResult) -> List[Any]:
        """
        Create tax forms section elements.

        Args:
            fifo_result: Result of FIFO calculation
            dividend_result: Result of dividend calculation

        Returns:
            List of flowable elements
        """
        elements = []

        # Chapter title
        elements.append(Paragraph("3. Dane do formularzy podatkowych", self.styles['ReportChapter']))

        # Calculate PIT-38 data
        fifo_df = fifo_result.to_dataframe()

        total_income = Decimal('0')
        total_cost = Decimal('0')
        profit = Decimal('0')
        loss = Decimal('0')

        if not fifo_df.empty:
            total_income = sum(match.income_pln for match in fifo_result.matches)
            total_cost = sum(match.cost_pln for match in fifo_result.matches)

            if total_income > total_cost:
                profit = total_income - total_cost
                loss = Decimal('0')
            else:
                profit = Decimal('0')
                loss = total_cost - total_income

        # Calculate tax base and due (rounded to full PLN)
        tax_base = int(profit)
        tax_due = int(tax_base * Decimal('0.19'))

        # PIT-38 form data
        elements.append(Paragraph("3.1 Dane do deklaracji PIT-38", self.styles['ReportSection']))

        # Table data for PIT-38
        pit38_data = [
            ["Sekcja", "Opis", "Wartość (PLN)"],
            ["C.22", "Przychód", self.format_currency(total_income)],
            ["C.23", "Koszty uzyskania przychodu", self.format_currency(total_cost)],
            ["C.24", "Razem przychód", self.format_currency(total_income)],
            ["C.25", "Razem koszty", self.format_currency(total_cost)],
            ["C.26", "Dochód (jeżeli C.24 > C.25)", self.format_currency(profit)],
            ["C.27", "Strata (jeżeli C.24 < C.25)", self.format_currency(loss)],
            ["D.29", "Podstawa obliczenia podatku (po zaokrągleniu)", str(tax_base)],
            ["D.31", "Podatek należny (19%)", str(tax_due)]
        ]

        # Create table
        pit38_table = Table(pit38_data, colWidths=[1.5 * cm, 7 * cm, 3 * cm])
        pit38_style = TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),

            # Data style
            ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ])
        pit38_table.setStyle(pit38_style)

        elements.append(pit38_table)

        # PIT-38 dividend section (Section G)
        if dividend_result.summaries:
            elements.append(Paragraph("3.1.1 Sekcja G - Dywidendy zagraniczne", self.styles['ReportSection']))

            # Table header with wrapped text
            g_header = [
                self._create_wrapped_header_cell("Państwo"),
                self._create_wrapped_header_cell("Przychód (PLN)"),
                self._create_wrapped_header_cell("Podatek należny 19% (PLN)"),
                self._create_wrapped_header_cell("Podatek zapłacony za granicą (PLN)"),
                self._create_wrapped_header_cell("Różnica (PLN)")
            ]

            # Table data
            g_data = [g_header]

            total_dividend = Decimal('0')
            total_tax_poland = Decimal('0')
            total_tax_abroad = Decimal('0')
            total_tax_to_pay = Decimal('0')

            for i, (country, summary) in enumerate(sorted(dividend_result.summaries.items()), 1):
                g_data.append([
                    f"G.{43 + i - 1}-{47 + i - 1} {country}",
                    self.format_currency(summary.total_dividend_pln),
                    self.format_currency(summary.tax_due_poland),
                    self.format_currency(summary.tax_paid_abroad_pln),
                    self.format_currency(summary.tax_to_pay)
                ])

                total_dividend += summary.total_dividend_pln
                total_tax_poland += summary.tax_due_poland
                total_tax_abroad += summary.tax_paid_abroad_pln
                total_tax_to_pay += summary.tax_to_pay

            # Add total row
            g_data.append([
                "RAZEM",
                self.format_currency(total_dividend),
                self.format_currency(total_tax_poland),
                self.format_currency(total_tax_abroad),
                self.format_currency(total_tax_to_pay)
            ])

            # Create table
            g_table = Table(g_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
            g_style = TableStyle([
                # Header style with improved padding and alignment for wrapped text
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                # Data style
                ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

                # Total row style
                ('FONTNAME', (0, -1), (-1, -1), self.bold_font_name),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ])
            g_table.setStyle(g_style)

            elements.append(g_table)

        else:
            elements.append(Paragraph("3.1.1 Sekcja G - Dywidendy zagraniczne", self.styles['ReportSection']))
            elements.append(Paragraph("Brak dywidend zagranicznych do wykazania w sekcji G.",
                                      self.styles['ReportBodyText']))

        # PIT/ZG section
        elements.append(Paragraph("3.2 Dane do załącznika PIT/ZG", self.styles['ReportSection']))

        if not fifo_df.empty:
            # Group by country
            country_groups = fifo_df.groupby('country')

            # Table header with wrapped text
            pitzg_header = [
                self._create_wrapped_header_cell("Państwo"),
                self._create_wrapped_header_cell("Przychód (PLN)"),
                self._create_wrapped_header_cell("Koszty (PLN)"),
                self._create_wrapped_header_cell("Dochód (PLN)"),
                self._create_wrapped_header_cell("Podatek zapłacony za granicą (PLN)")
            ]

            # Table data
            pitzg_data = [pitzg_header]

            for country, group in sorted(country_groups):
                securities_income = Decimal(str(group['income_pln'].sum()))
                securities_cost = Decimal(str(group['cost_pln'].sum()))
                securities_profit = max(Decimal('0'), securities_income - securities_cost)

                pitzg_data.append([
                    country,
                    self.format_currency(securities_income),
                    self.format_currency(securities_cost),
                    self.format_currency(securities_profit),
                    "0,00"  # Usually 0 for securities
                ])

            # Create table
            pitzg_table = Table(pitzg_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm, 4 * cm])
            pitzg_style = TableStyle([
                # Header style with improved padding and alignment for wrapped text
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                # Data style
                ('FONTNAME', (0, 1), (-1, -1), self.base_font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ])
            pitzg_table.setStyle(pitzg_style)

            elements.append(pitzg_table)

            # Add note about dividends in PIT/ZG
            if dividend_result.summaries:
                elements.append(Paragraph("3.2.1 Uwaga dotycząca dywidend w PIT/ZG", self.styles['ReportSection']))
                elements.append(Paragraph(
                    "Zgodnie z zasadami podatkowymi, dywidendy uwzględnione w sekcji G formularza PIT-38 NIE są "
                    "wykazywane ponownie w załączniku PIT/ZG.",
                    self.styles['ReportBodyText']
                ))
        else:
            elements.append(Paragraph("Brak danych do wykazania w załączniku PIT/ZG.",
                                      self.styles['ReportBodyText']))

        return elements


    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Export tax calculation results to a PDF report.

        Args:
            data: Dictionary with calculation results
            output_path: Path to the output PDF file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            self.logger.info(f"Using font: {self.base_font_name}")
            self.logger.info(f"All registered fonts: {list(pdfmetrics.getRegisteredFontNames())}")
            tax_year = data.get('tax_year')
            fifo_result = data.get('fifo_result')
            dividend_result = data.get('dividend_result')

            # Make sure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Create PDF document with metadata to fix the anonymous title issue
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

            # Set document metadata to fix the anonymous title
            doc.title = "Trading212 Tax Calculator Report"
            doc.author = "Trading212 Tax Calculator"
            doc.subject = f"Raport podatkowy" + (f" {tax_year}" if tax_year else "")
            doc.creator = "Trading212 Tax Calculator"
            # List to store PDF elements
            elements = []

            # Create title page
            elements.extend(self.create_title_page(tax_year))

            # Create FIFO section
            elements.extend(self.create_fifo_section(fifo_result))

            # Create dividend section
            elements.extend(self.create_dividend_section(dividend_result))

            # Create tax forms section
            elements.extend(self.create_tax_forms_section(fifo_result, dividend_result))

            # Build the PDF
            doc.build(elements)

            self.logger.info(f"PDF report saved to {output_path}")
            print(f"PDF report saved to {output_path}")

            return True

        except Exception as e:
            import traceback
            self.logger.error(f"Error exporting PDF report: {e}")
            self.logger.error(traceback.format_exc())
            print(f"Error exporting PDF report: {e}")
            return False