"""
PDF Report Exporter using ReportLab with Polish character support.
"""

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from calculators.dividend_calculator import DividendCalculationResult
from calculators.fifo_calculator import FifoCalculationResult
from calculators.interest_calculator import InterestCalculationResult
from exporters.exporter_interface import ExporterInterface

logger = logging.getLogger(__name__)


class ReportLabExporter(ExporterInterface[Dict[str, Any]]):
    """Export tax report data to PDF format with Polish character support."""

    # Default font fallback chain
    DEFAULT_FONT_CHAIN = ["DejaVuSans", "Arial", "Helvetica"]

    def __init__(
        self,
        personal_data: Optional[Dict[str, str]] = None,
        custom_font_path: Optional[str] = None,
        custom_font_name: Optional[str] = None,
    ):
        """
        Initialize the PDF exporter.

        Args:
            personal_data: Dictionary containing personal information for the report
            custom_font_path: Path to a custom TTF font file (e.g., FiraCode Nerd Font)
            custom_font_name: Name to register the custom font under
        """
        self.personal_data = personal_data or {}
        self.custom_font_path = custom_font_path
        self.custom_font_name = custom_font_name
        self.font_name = "Helvetica"  # Default fallback
        self.font_name_bold = "Helvetica-Bold"
        self._register_fonts()
        self.styles = self._create_custom_styles()

    def _register_fonts(self):
        """Register fonts with Polish character support."""
        font_registered = False

        # Try custom font first if provided
        if self.custom_font_path and self.custom_font_name:
            try:
                if os.path.exists(self.custom_font_path):
                    pdfmetrics.registerFont(TTFont(self.custom_font_name, self.custom_font_path))
                    self.font_name = self.custom_font_name
                    self.font_name_bold = self.custom_font_name  # Use same font for bold

                    # Try to find bold variant
                    bold_path = self.custom_font_path.replace(".ttf", "-Bold.ttf")
                    if os.path.exists(bold_path):
                        bold_name = f"{self.custom_font_name}-Bold"
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                        self.font_name_bold = bold_name

                    logger.info(f"Registered custom font: {self.custom_font_name}")
                    font_registered = True
                else:
                    logger.warning(f"Custom font path not found: {self.custom_font_path}")
            except Exception as e:
                logger.warning(f"Failed to register custom font: {e}")

        if font_registered:
            return

        # Build list of potential font paths
        font_paths = []

        # Linux font directories
        linux_dirs = [
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/TTF",
            "/usr/share/fonts/dejavu",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]

        # Windows font directory
        windows_font_dir = os.environ.get("WINDIR")
        if windows_font_dir:
            linux_dirs.append(os.path.join(windows_font_dir, "Fonts"))

        # macOS font directories
        macos_dirs = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]

        font_paths.extend(linux_dirs)
        font_paths.extend(macos_dirs)

        # Try DejaVu Sans (best Polish support, commonly available on Linux)
        for font_dir in font_paths:
            dejavu_path = os.path.join(font_dir, "DejaVuSans.ttf")
            dejavu_bold_path = os.path.join(font_dir, "DejaVuSans-Bold.ttf")

            if os.path.exists(dejavu_path):
                try:
                    pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_path))
                    self.font_name = "DejaVuSans"
                    logger.info(f"Registered DejaVuSans from {dejavu_path}")

                    if os.path.exists(dejavu_bold_path):
                        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", dejavu_bold_path))
                        self.font_name_bold = "DejaVuSans-Bold"
                        logger.info(f"Registered DejaVuSans-Bold from {dejavu_bold_path}")
                    else:
                        self.font_name_bold = "DejaVuSans"

                    font_registered = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to register DejaVuSans: {e}")

        if font_registered:
            return

        # Try Arial (Windows, good Polish support)
        for font_dir in font_paths:
            arial_path = os.path.join(font_dir, "arial.ttf")
            arial_bold_path = os.path.join(font_dir, "arialbd.ttf")

            # Also try capitalized names (Linux often has Arial.ttf)
            if not os.path.exists(arial_path):
                arial_path = os.path.join(font_dir, "Arial.ttf")
            if not os.path.exists(arial_bold_path):
                arial_bold_path = os.path.join(font_dir, "Arial-Bold.ttf")

            if os.path.exists(arial_path):
                try:
                    pdfmetrics.registerFont(TTFont("Arial", arial_path))
                    self.font_name = "Arial"
                    logger.info(f"Registered Arial from {arial_path}")

                    if os.path.exists(arial_bold_path):
                        pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold_path))
                        self.font_name_bold = "Arial-Bold"
                    else:
                        self.font_name_bold = "Arial"

                    font_registered = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to register Arial: {e}")

        if font_registered:
            return

        # Fall back to Helvetica (built-in, limited Polish support)
        logger.warning(
            "Could not find DejaVuSans or Arial fonts. "
            "Using Helvetica (Polish characters may not display correctly). "
            "Install DejaVu fonts: apt-get install fonts-dejavu-core"
        )
        self.font_name = "Helvetica"
        self.font_name_bold = "Helvetica-Bold"

    def _create_custom_styles(self):
        """Create custom paragraph styles with the registered font."""
        styles = getSampleStyleSheet()

        # Title style
        styles.add(
            ParagraphStyle(
                name="CustomTitle",
                fontName=self.font_name_bold,
                fontSize=18,
                alignment=1,  # Center
                spaceAfter=20,
            )
        )

        # Subtitle style
        styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                fontName=self.font_name,
                fontSize=14,
                alignment=1,
                spaceAfter=10,
            )
        )

        # Section header style
        styles.add(
            ParagraphStyle(
                name="SectionHeader",
                fontName=self.font_name_bold,
                fontSize=12,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        # Normal text style
        styles.add(
            ParagraphStyle(
                name="CustomNormal",
                fontName=self.font_name,
                fontSize=10,
                spaceAfter=6,
            )
        )

        # Table header style
        styles.add(
            ParagraphStyle(
                name="TableHeader",
                fontName=self.font_name_bold,
                fontSize=8,
                alignment=1,
            )
        )

        # Table cell style
        styles.add(
            ParagraphStyle(
                name="TableCell",
                fontName=self.font_name,
                fontSize=8,
            )
        )

        return styles

    def _create_wrapped_header_cell(self, text):
        """Create a wrapped header cell with proper Polish characters."""
        return Paragraph(text, self.styles["TableHeader"])

    def format_decimal(self, value: Decimal, decimals: int = 2) -> str:
        """Format a decimal value with Polish number formatting (comma as decimal separator)."""
        try:
            if isinstance(value, str):
                value = Decimal(value.replace(",", "."))

            if abs(value) < 1 and value != 0:
                actual_decimals = max(5, decimals)
            elif value == int(value):
                actual_decimals = 0
            else:
                actual_decimals = decimals

            formatted = str(round(float(value), actual_decimals)).replace(".", ",")

            if "," in formatted:
                integer_part, decimal_part = formatted.split(",")
                if not (abs(value) < 1 and value != 0):
                    decimal_part = decimal_part.ljust(actual_decimals, "0")
                formatted = f"{integer_part},{decimal_part}"
            elif actual_decimals > 0:
                formatted = f"{formatted},{'0' * actual_decimals}"

            return formatted
        except Exception:
            return str(value)

    def format_date(self, date) -> str:
        """Format a date for display."""
        if isinstance(date, str):
            try:
                date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return date
        return date.strftime("%Y-%m-%d")

    def format_currency(self, value: Decimal) -> str:
        """Format a currency value with 2 decimal places."""
        try:
            if isinstance(value, str):
                value = Decimal(value.replace(",", "."))

            formatted = str(round(float(value), 2)).replace(".", ",")

            if "," in formatted:
                integer_part, decimal_part = formatted.split(",")
                formatted = f"{integer_part},{decimal_part.ljust(2, '0')}"
            else:
                formatted = f"{formatted},00"

            return formatted
        except Exception:
            return str(value)

    def create_title_page(self, tax_year: Optional[int] = None) -> List[Any]:
        """Create the title page elements with proper Polish characters."""
        elements = []

        # Title
        title = "Raport Podatkowy Trading212"
        if tax_year:
            title += f" - Rok {tax_year}"
        elements.append(Paragraph(title, self.styles["CustomTitle"]))

        # Subtitle with proper Polish characters
        subtitle = "Rozliczenie sprzedaży akcji i dywidend"
        elements.append(Paragraph(subtitle, self.styles["CustomSubtitle"]))
        elements.append(Spacer(1, 20))

        # Personal data section with proper Polish characters
        fullname = self.personal_data.get("FULLNAME", "UZUPEŁNIJ IMIĘ I NAZWISKO")
        pesel = self.personal_data.get("PESEL", "UZUPEŁNIJ PESEL")
        address = self.personal_data.get("ADDRESS", "UZUPEŁNIJ ADRES")
        city = self.personal_data.get("CITY", "UZUPEŁNIJ MIASTO")
        postal_code = self.personal_data.get("POSTAL_CODE", "UZUPEŁNIJ KOD POCZTOWY")
        tax_office = self.personal_data.get("TAX_OFFICE", "UZUPEŁNIJ URZĄD SKARBOWY")

        personal_data = [
            ["Imię i nazwisko:", fullname],
            ["PESEL:", pesel],
            ["Adres:", address],
            ["Miasto:", city],
            ["Kod pocztowy:", postal_code],
            ["Urząd Skarbowy:", tax_office],
        ]

        personal_table = Table(personal_data, colWidths=[4 * cm, 10 * cm])
        personal_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                    ("FONTNAME", (0, 0), (0, -1), self.font_name_bold),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(personal_table)
        elements.append(Spacer(1, 30))

        return elements

    def create_fifo_section(self, fifo_result: FifoCalculationResult) -> List[Any]:
        """Create the FIFO calculation section with proper Polish characters."""
        elements = []

        # Section header
        elements.append(
            Paragraph(
                "Szczegółowy Raport Transakcji Akcji (Metoda FIFO)", self.styles["SectionHeader"]
            )
        )

        # Column widths for transaction tables
        col_widths = [
            2.0 * cm,
            1.5 * cm,
            3.5 * cm,
            1.2 * cm,
            1.5 * cm,
            1.5 * cm,
            1.5 * cm,
            2.0 * cm,
            2.0 * cm,
            1.8 * cm,
        ]

        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )

        # Buy transactions section
        elements.append(Paragraph("Transakcje Kupna", self.styles["SectionHeader"]))

        buy_transactions = {}
        for match in fifo_result.matches:
            buy_key = (match.buy_transaction.ticker, match.buy_date)
            if buy_key not in buy_transactions:
                buy_transactions[buy_key] = match.buy_transaction

        # Header with proper Polish characters
        buy_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Data",
                "Ticker",
                "Nazwa",
                "Ilość",
                "Cena",
                "Waluta",
                "Kurs NBP",
                "Wartość waluta",
                "Wartość PLN",
                "Opłaty PLN",
            ]
        ]
        buy_data = [buy_header]

        for (ticker, date), tx in sorted(buy_transactions.items(), key=lambda x: x[0][1]):
            ex_rate = (
                self.format_decimal(tx.exchange_rate, 5)
                if tx.currency == "GBX"
                else self.format_decimal(tx.exchange_rate)
            )
            buy_data.append(
                [
                    self.format_date(date),
                    ticker,
                    (tx.name or "")[:20],
                    self.format_decimal(tx.quantity, 0),
                    self.format_decimal(tx.price_per_share),
                    tx.currency,
                    ex_rate,
                    self.format_decimal(tx.total_value_foreign),
                    self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal("0")),
                ]
            )

        buy_table = Table(buy_data, colWidths=col_widths, repeatRows=1)
        buy_table.setStyle(table_style)
        elements.append(buy_table)
        elements.append(Spacer(1, 15))

        # Sell transactions section
        elements.append(Paragraph("Transakcje Sprzedaży", self.styles["SectionHeader"]))

        sell_transactions = {}
        for match in fifo_result.matches:
            sell_key = (match.sell_transaction.ticker, match.sell_date)
            if sell_key not in sell_transactions:
                sell_transactions[sell_key] = match.sell_transaction

        sell_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Data",
                "Ticker",
                "Nazwa",
                "Ilość",
                "Cena",
                "Waluta",
                "Kurs NBP",
                "Wartość waluta",
                "Wartość PLN",
                "Opłaty PLN",
            ]
        ]
        sell_data = [sell_header]

        for (ticker, date), tx in sorted(sell_transactions.items(), key=lambda x: x[0][1]):
            ex_rate = (
                self.format_decimal(tx.exchange_rate, 5)
                if tx.currency == "GBX"
                else self.format_decimal(tx.exchange_rate)
            )
            sell_data.append(
                [
                    self.format_date(date),
                    ticker,
                    (tx.name or "")[:20],
                    self.format_decimal(tx.quantity, 0),
                    self.format_decimal(tx.price_per_share),
                    tx.currency,
                    ex_rate,
                    self.format_decimal(tx.total_value_foreign),
                    self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal("0")),
                ]
            )

        sell_table = Table(sell_data, colWidths=col_widths, repeatRows=1)
        sell_table.setStyle(table_style)
        elements.append(sell_table)
        elements.append(Spacer(1, 15))

        # FIFO Matches section
        elements.append(
            Paragraph("Dopasowania FIFO (Kupno-Sprzedaż)", self.styles["SectionHeader"])
        )

        match_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Ticker",
                "Data zakupu",
                "Data sprzedaży",
                "Liczba akcji",
                "Przychód PLN",
                "Koszt PLN",
                "Dochód/Strata PLN",
                "% zysku/straty",
                "Kraj",
            ]
        ]
        match_col_widths = [
            1.5 * cm,
            2.0 * cm,
            2.0 * cm,
            1.5 * cm,
            2.0 * cm,
            2.0 * cm,
            2.0 * cm,
            2.0 * cm,
            3.0 * cm,
        ]
        matches_data = [match_header]

        for match in sorted(fifo_result.matches, key=lambda m: m.sell_date):
            profit_pct = (match.profit_loss_pln / match.cost_pln) * 100 if match.cost_pln > 0 else 0
            matches_data.append(
                [
                    match.sell_transaction.ticker,
                    self.format_date(match.buy_date),
                    self.format_date(match.sell_date),
                    self.format_decimal(match.used_quantity, 0),
                    self.format_currency(match.income_pln),
                    self.format_currency(match.cost_pln),
                    self.format_currency(match.profit_loss_pln),
                    f"{self.format_decimal(profit_pct, 1)}%",
                    match.country or "Nieznany",
                ]
            )

        matches_table = Table(matches_data, colWidths=match_col_widths, repeatRows=1)
        matches_table.setStyle(table_style)
        elements.append(matches_table)
        elements.append(Spacer(1, 20))

        # Summary section with proper Polish characters
        elements.append(Paragraph("Podsumowanie Transakcji Akcji", self.styles["SectionHeader"]))

        total_income = sum(m.income_pln for m in fifo_result.matches)
        total_cost = sum(m.cost_pln for m in fifo_result.matches)
        total_profit = sum(m.profit_loss_pln for m in fifo_result.matches if m.profit_loss_pln > 0)
        total_loss = sum(
            abs(m.profit_loss_pln) for m in fifo_result.matches if m.profit_loss_pln < 0
        )
        tax_base = int(max(0, total_profit - total_loss))
        tax_due = int(tax_base * Decimal("0.19"))

        summary_data = [
            ["Pozycja", "Wartość (PLN)"],
            ["Łączny przychód", self.format_currency(total_income)],
            ["Łączny koszt uzyskania przychodu", self.format_currency(total_cost)],
            ["Łączny zysk", self.format_currency(total_profit)],
            ["Łączna strata", self.format_currency(total_loss)],
            ["Podstawa opodatkowania", self.format_currency(Decimal(tax_base))],
            ["Podatek należny (19%)", self.format_currency(Decimal(tax_due))],
        ]

        summary_table = Table(summary_data, colWidths=[10 * cm, 5 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        return elements

    def _create_transaction_details(self, fifo_result: FifoCalculationResult) -> List[Any]:
        """Create detailed transaction breakdown with proper Polish characters."""
        elements = []

        # Group matches by ticker
        matches_by_ticker = {}
        for match in fifo_result.matches:
            ticker = match.sell_transaction.ticker
            if ticker not in matches_by_ticker:
                matches_by_ticker[ticker] = []
            matches_by_ticker[ticker].append(match)

        for ticker, matches in sorted(matches_by_ticker.items()):
            sell_tx = matches[0].sell_transaction

            tx_details = [
                ["Ticker:", ticker],
                ["Nazwa:", (sell_tx.name or "")[:30]],
                ["Liczba transakcji:", str(len(matches))],
            ]
            tx_table = Table(tx_details, colWidths=[5 * cm, 10 * cm])
            tx_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                        ("FONTNAME", (0, 0), (0, -1), self.font_name_bold),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            elements.append(tx_table)

            for match in matches:
                buy_tx = match.buy_transaction
                detail_text = (
                    f"  Kupno: {self.format_date(match.buy_date)} - "
                    f"{self.format_decimal(match.used_quantity, 0)} akcji @ "
                    f"{self.format_decimal(buy_tx.price_per_share)} {buy_tx.currency}"
                )
                elements.append(Paragraph(detail_text, self.styles["CustomNormal"]))

            elements.append(Spacer(1, 10))

        return elements

    def create_dividend_section(self, dividend_result: DividendCalculationResult) -> List[Any]:
        """Create the dividend section with proper Polish characters."""
        elements = []

        elements.append(Paragraph("Szczegółowy Raport Dywidend", self.styles["SectionHeader"]))

        # Summary by country
        elements.append(Paragraph("Podsumowanie według Kraju", self.styles["SectionHeader"]))

        summary_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Państwo",
                "Dywidenda PLN",
                "Podatek pobrany PLN",
                "Podatek PL 19%",
                "Do zapłaty PL",
            ]
        ]
        summary_data = [summary_header]

        total_dividend = total_tax_abroad = total_tax_poland = total_tax_to_pay = Decimal("0")

        for country, summary in sorted(dividend_result.summaries.items()):
            summary_data.append(
                [
                    country,
                    self.format_currency(summary.total_dividend_pln),
                    self.format_currency(summary.tax_paid_abroad_pln),
                    self.format_currency(summary.tax_due_poland),
                    self.format_currency(summary.tax_to_pay),
                ]
            )
            total_dividend += summary.total_dividend_pln
            total_tax_abroad += summary.tax_paid_abroad_pln
            total_tax_poland += summary.tax_due_poland
            total_tax_to_pay += summary.tax_to_pay

        # Add totals row
        summary_data.append(
            [
                "RAZEM",
                self.format_currency(total_dividend),
                self.format_currency(total_tax_abroad),
                self.format_currency(total_tax_poland),
                self.format_currency(total_tax_to_pay),
            ]
        )

        summary_table = Table(
            summary_data, colWidths=[4.0 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm], repeatRows=1
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, -1), (-1, -1), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -2), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 15))

        # Detailed dividend transactions
        elements.append(Paragraph("Szczegółowe Transakcje Dywidend", self.styles["SectionHeader"]))

        div_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Data",
                "Ticker",
                "Nazwa",
                "Ilość",
                "Dyw/akcję",
                "Waluta",
                "Kurs NBP",
                "Wart. waluta",
                "Wart. PLN",
                "Pod. pobrany",
                "Pod. PLN",
            ]
        ]
        div_col_widths = [
            1.8 * cm,
            1.3 * cm,
            2.5 * cm,
            1.0 * cm,
            1.7 * cm,
            1.2 * cm,
            1.5 * cm,
            1.8 * cm,
            1.8 * cm,
            1.7 * cm,
            1.7 * cm,
        ]
        div_data = [div_header]

        for country, summary in sorted(dividend_result.summaries.items()):
            for tx in sorted(summary.transactions, key=lambda x: x.date):
                div_per_share = (
                    tx.total_value_foreign / tx.quantity if tx.quantity > 0 else Decimal("0")
                )
                div_data.append(
                    [
                        self.format_date(tx.date),
                        tx.ticker,
                        (tx.name or "")[:15],
                        self.format_decimal(tx.quantity, 0),
                        self.format_decimal(div_per_share, 4),
                        tx.currency,
                        self.format_decimal(tx.exchange_rate),
                        self.format_decimal(tx.total_value_foreign),
                        self.format_currency(tx.total_value_pln),
                        self.format_currency(tx.withholding_tax_pln or Decimal("0")),
                        self.format_currency(tx.total_value_pln * Decimal("0.19")),
                    ]
                )

        div_table = Table(div_data, colWidths=div_col_widths, repeatRows=1)
        div_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(div_table)
        elements.append(Spacer(1, 15))

        # Country summary boxes
        for country, summary in sorted(dividend_result.summaries.items()):
            elements.append(Paragraph(f"Podsumowanie: {country}", self.styles["SectionHeader"]))

            cs_data = [
                ["Suma dywidend", self.format_currency(summary.total_dividend_pln)],
                ["Podatek pobrany za granicą", self.format_currency(summary.tax_paid_abroad_pln)],
                ["Podatek należny w Polsce (19%)", self.format_currency(summary.tax_due_poland)],
                ["Podatek do zapłaty", self.format_currency(summary.tax_to_pay)],
            ]
            cs_table = Table(cs_data, colWidths=[6 * cm, 3 * cm])
            cs_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                        ("FONTNAME", (0, 0), (0, -1), self.font_name_bold),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(cs_table)
            elements.append(Spacer(1, 10))

        return elements

    def create_interest_section(self, interest_result: InterestCalculationResult) -> List[Any]:
        """Create the interest section with proper Polish characters."""
        elements = []

        elements.append(
            Paragraph("Raport Odsetek od Środków Pieniężnych", self.styles["SectionHeader"])
        )

        # Calculate tax values from total_interest_pln
        total_interest = interest_result.total_interest_pln
        tax_due = total_interest * Decimal("0.19")
        tax_to_pay = Decimal(int(tax_due))  # Round down to full PLN

        summary_data = [
            ["Pozycja", "Wartość"],
            ["Łączne odsetki (PLN)", self.format_currency(total_interest)],
            ["Podatek należny (19%)", self.format_currency(tax_due)],
            ["Podatek do zapłaty", self.format_currency(tax_to_pay)],
        ]

        summary_table = Table(summary_data, colWidths=[8 * cm, 7 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        return elements

    def create_pit38_summary(
        self,
        fifo_result: FifoCalculationResult,
        dividend_result: DividendCalculationResult,
        interest_result: InterestCalculationResult,
    ) -> List[Any]:
        """Create PIT-38 summary section with proper Polish characters."""
        elements = []

        elements.append(Paragraph("Podsumowanie PIT-38", self.styles["SectionHeader"]))

        # Securities (stocks) section
        fifo_df = fifo_result.to_dataframe()
        total_income = total_cost = profit = loss = Decimal("0")

        if not fifo_df.empty:
            total_income = Decimal(str(fifo_df["income_pln"].sum()))
            total_cost = Decimal(str(fifo_df["cost_pln"].sum()))

        if total_income > total_cost:
            profit = total_income - total_cost
        else:
            loss = total_cost - total_income

        tax_base = int(profit)
        tax_due = int(tax_base * Decimal("0.19"))

        pit38_data = [
            ["Sekcja", "Opis", "Wartość PLN"],
            [
                "C.22",
                "Przychód ze sprzedaży papierów wartościowych",
                self.format_currency(total_income),
            ],
            ["C.23", "Koszty uzyskania przychodu", self.format_currency(total_cost)],
            ["C.24", "Zysk", self.format_currency(profit)],
            ["C.25", "Strata", self.format_currency(loss)],
            ["C.26", "Podstawa opodatkowania", self.format_currency(Decimal(tax_base))],
            ["C.27", "Podatek należny (19%)", self.format_currency(Decimal(tax_due))],
        ]

        pit38_table = Table(pit38_data, colWidths=[1.5 * cm, 7 * cm, 3 * cm])
        pit38_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(pit38_table)
        elements.append(Spacer(1, 15))

        # Dividends section (Section G)
        elements.append(Paragraph("Sekcja G - Dywidendy Zagraniczne", self.styles["SectionHeader"]))

        g_header = [
            self._create_wrapped_header_cell(h)
            for h in [
                "Państwo",
                "Przychód PLN",
                "Podatek należny 19%",
                "Podatek zapłacony za granicą",
                "Różnica",
            ]
        ]
        g_data = [g_header]

        for country, summary in sorted(dividend_result.summaries.items()):
            g_data.append(
                [
                    country,
                    self.format_currency(summary.total_dividend_pln),
                    self.format_currency(summary.tax_due_poland),
                    self.format_currency(summary.tax_paid_abroad_pln),
                    self.format_currency(summary.tax_to_pay),
                ]
            )

        g_table = Table(g_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
        g_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(g_table)
        elements.append(Spacer(1, 15))

        # Interest section
        elements.append(
            Paragraph("Sekcja - Odsetki od Środków Pieniężnych", self.styles["SectionHeader"])
        )

        # Calculate tax values from total_interest_pln
        total_interest = interest_result.total_interest_pln
        interest_tax_due = total_interest * Decimal("0.19")
        interest_tax_to_pay = Decimal(int(interest_tax_due))  # Round down to full PLN

        int_data = [
            ["Pozycja", "Wartość PLN"],
            ["Łączne odsetki", self.format_currency(total_interest)],
            ["Podatek należny (19%)", self.format_currency(interest_tax_due)],
            ["Podatek do zapłaty", self.format_currency(interest_tax_to_pay)],
        ]
        int_table = Table(int_data, colWidths=[8 * cm, 5 * cm])
        int_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(int_table)
        elements.append(Spacer(1, 20))

        return elements

    def create_pitzg_section(self, fifo_result: FifoCalculationResult) -> List[Any]:
        """Create PIT/ZG section with proper Polish characters."""
        elements = []

        elements.append(
            Paragraph("Załącznik PIT/ZG - Dochody Zagraniczne", self.styles["SectionHeader"])
        )

        fifo_df = fifo_result.to_dataframe()

        if fifo_df.empty:
            elements.append(
                Paragraph(
                    "Brak transakcji zagranicznych do wykazania w PIT/ZG.",
                    self.styles["CustomNormal"],
                )
            )
            return elements

        country_groups = fifo_df.groupby("country")

        pitzg_header = [
            self._create_wrapped_header_cell(h)
            for h in ["Państwo", "Przychód PLN", "Koszty PLN", "Dochód PLN", "Podatek zapłacony"]
        ]
        pitzg_data = [pitzg_header]

        for country, group in country_groups:
            sec_income = Decimal(str(group["income_pln"].sum()))
            sec_cost = Decimal(str(group["cost_pln"].sum()))
            sec_profit = max(Decimal("0"), sec_income - sec_cost)

            pitzg_data.append(
                [
                    country,
                    self.format_currency(sec_income),
                    self.format_currency(sec_cost),
                    self.format_currency(sec_profit),
                    "0,00",  # Tax paid abroad (usually 0 for securities)
                ]
            )

        pitzg_table = Table(pitzg_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm, 4 * cm])
        pitzg_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), self.font_name_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self.font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(pitzg_table)
        elements.append(Spacer(1, 10))

        # Note about verification
        elements.append(
            Paragraph(
                "Uwaga: Kraje oznaczone '(from ISIN)' zostały określone na podstawie kodu ISIN "
                "i mogą wymagać weryfikacji.",
                self.styles["CustomNormal"],
            )
        )

        return elements

    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Export tax report data to PDF.

        Args:
            data: Dictionary containing:
                - tax_year: Optional tax year
                - fifo_result: FifoCalculationResult
                - dividend_result: DividendCalculationResult
                - interest_result: InterestCalculationResult
            output_path: Path to save the PDF file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            tax_year = data.get("tax_year")
            fifo_result = data.get("fifo_result")
            dividend_result = data.get("dividend_result")
            interest_result = data.get("interest_result")

            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            # Build content
            elements = []

            # Title page
            elements.extend(self.create_title_page(tax_year))

            # FIFO section
            if fifo_result and fifo_result.matches:
                elements.extend(self.create_fifo_section(fifo_result))

            # Dividend section
            if dividend_result and dividend_result.summaries:
                elements.extend(self.create_dividend_section(dividend_result))

            # Interest section
            if interest_result and interest_result.total_interest_pln > 0:
                elements.extend(self.create_interest_section(interest_result))

            # PIT-38 summary
            if fifo_result and dividend_result and interest_result:
                elements.extend(
                    self.create_pit38_summary(fifo_result, dividend_result, interest_result)
                )

            # PIT/ZG section
            if fifo_result:
                elements.extend(self.create_pitzg_section(fifo_result))

            # Build PDF
            doc.build(elements)
            logger.info(f"PDF report exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export PDF report: {e}")
            return False
