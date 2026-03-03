import os
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from exporters.exporter_interface import ExporterInterface
from calculators.fifo_calculator import FifoCalculationResult
from calculators.dividend_calculator import DividendCalculationResult
from calculators.interest_calculator import InterestCalculationResult
from config.tax_treaties import has_tax_treaty

logger = logging.getLogger(__name__)


class ReportLabExporter(ExporterInterface[Dict[str, Any]]):
    """Exporter for tax calculation results to PDF report using ReportLab"""

    def __init__(self, personal_data: Optional[Dict[str, str]] = None):
        self.personal_data = personal_data or {}
        self.logger = logging.getLogger(__name__)
        self._register_fonts()
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _register_fonts(self):
        """Register fonts for Polish characters"""
        try:
            # macOS-specific font paths (commonly available fonts with Polish character support)
            macos_font_candidates = [
                ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 'ArialUnicode', None),
                ('/System/Library/Fonts/Helvetica.ttc', 'Helvetica', None),  # System Helvetica on macOS
                ('/Library/Fonts/Arial.ttf', 'Arial', '/Library/Fonts/Arial Bold.ttf'),
                ('/System/Library/Fonts/Supplemental/Arial.ttf', 'Arial', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
            ]

            # Try macOS fonts first
            for font_path, font_name, bold_path in macos_font_candidates:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        if bold_path and os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont(f'{font_name}-Bold', bold_path))
                            self.base_font_name = font_name
                            self.bold_font_name = f'{font_name}-Bold'
                        else:
                            self.base_font_name = font_name
                            self.bold_font_name = font_name
                        self.logger.info(f"Using {font_name} font from {font_path}")
                        return
                    except Exception as e:
                        self.logger.debug(f"Failed to register {font_name} from {font_path}: {e}")
                        continue

            # Standard font search paths for other systems
            font_paths = []
            windows_font_dir = os.environ.get('WINDIR')
            if windows_font_dir:
                font_paths.append(os.path.join(windows_font_dir, 'Fonts'))
            font_paths.extend([
                '/System/Library/Fonts',
                '/Library/Fonts',
                os.path.expanduser('~/Library/Fonts'),
                '/usr/share/fonts/truetype/dejavu',
                '/usr/share/fonts/TTF',
                '/usr/share/fonts/truetype',
                '/usr/share/fonts/truetype/liberation',
                '/usr/share/fonts/truetype/liberation2',
            ])

            # Try DejaVu fonts (best Polish support)
            for font_dir in font_paths:
                dejavu_path = os.path.join(font_dir, 'DejaVuSans.ttf')
                dejavu_bold_path = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')
                if os.path.exists(dejavu_path):
                    pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_path))
                    if os.path.exists(dejavu_bold_path):
                        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold_path))
                        self.base_font_name = 'DejaVuSans'
                        self.bold_font_name = 'DejaVuSans-Bold'
                    else:
                        self.base_font_name = 'DejaVuSans'
                        self.bold_font_name = 'DejaVuSans'
                    self.logger.info(f"Using DejaVu fonts from {font_dir}")
                    return

            # Try Arial fonts (good Polish support)
            for font_dir in font_paths:
                arial_path = os.path.join(font_dir, 'arial.ttf')
                arial_bold_path = os.path.join(font_dir, 'arialbd.ttf')
                if os.path.exists(arial_path):
                    pdfmetrics.registerFont(TTFont('Arial', arial_path))
                    if os.path.exists(arial_bold_path):
                        pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
                        self.base_font_name = 'Arial'
                        self.bold_font_name = 'Arial-Bold'
                    else:
                        self.base_font_name = 'Arial'
                        self.bold_font_name = 'Arial'
                    self.logger.info(f"Using Arial fonts from {font_dir}")
                    return

            # Try Liberation fonts (good Polish support, common on Linux)
            for font_dir in font_paths:
                liberation_path = os.path.join(font_dir, 'LiberationSans-Regular.ttf')
                liberation_bold_path = os.path.join(font_dir, 'LiberationSans-Bold.ttf')
                if os.path.exists(liberation_path):
                    pdfmetrics.registerFont(TTFont('LiberationSans', liberation_path))
                    if os.path.exists(liberation_bold_path):
                        pdfmetrics.registerFont(TTFont('LiberationSans-Bold', liberation_bold_path))
                        self.base_font_name = 'LiberationSans'
                        self.bold_font_name = 'LiberationSans-Bold'
                    else:
                        self.base_font_name = 'LiberationSans'
                        self.bold_font_name = 'LiberationSans'
                    self.logger.info(f"Using Liberation fonts from {font_dir}")
                    return

        except Exception as e:
            self.logger.error(f"Error registering fonts: {e}")

        # Fallback to Helvetica with clear warning
        self.base_font_name = 'Helvetica'
        self.bold_font_name = 'Helvetica-Bold'
        self.logger.warning("=" * 80)
        self.logger.warning("WARNING: No Unicode-compatible fonts found!")
        self.logger.warning("Polish characters (ą, ć, ę, ł, ń, ó, ś, ź, ż) will NOT render correctly in PDF.")
        self.logger.warning("")
        self.logger.warning("To fix this, install DejaVu fonts:")
        self.logger.warning("  macOS:   brew install --cask font-dejavu")
        self.logger.warning("  Ubuntu:  sudo apt-get install fonts-dejavu")
        self.logger.warning("  Fedora:  sudo dnf install dejavu-sans-fonts")
        self.logger.warning("=" * 80)
        print("\n⚠️  WARNING: Polish characters may not display correctly in PDF!")
        print("   Install DejaVu fonts for proper Polish character support.")
        print("   See log for installation instructions.\n")

    def _create_custom_styles(self):
        self.styles.add(ParagraphStyle(name='ReportTitle', parent=self.styles['Title'],
            fontName=self.bold_font_name, fontSize=16, alignment=TA_CENTER, spaceAfter=12))
        self.styles.add(ParagraphStyle(name='ReportChapter', parent=self.styles['Heading1'],
            fontName=self.bold_font_name, fontSize=14, alignment=TA_LEFT, spaceAfter=10))
        self.styles.add(ParagraphStyle(name='ReportSection', parent=self.styles['Heading2'],
            fontName=self.bold_font_name, fontSize=12, alignment=TA_LEFT, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='ReportBodyText', parent=self.styles['Normal'],
            fontName=self.base_font_name, fontSize=10, alignment=TA_LEFT, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='TableHeader', parent=self.styles['Normal'],
            fontName=self.bold_font_name, fontSize=8, alignment=TA_CENTER, leading=10))
        self.summary_table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.base_font_name), ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9), ('ALIGN', (0, 0), (0, -1), 'LEFT'), ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)])

    def _create_wrapped_header_cell(self, text):
        return Paragraph(text, self.styles['TableHeader'])

    def format_decimal(self, value: Decimal, decimals: int = 2) -> str:
        if value is None: return "0,00"
        if isinstance(value, str):
            try: value = Decimal(value.replace(',', '.'))
            except: return value
        if abs(value) < 1 and value != 0: actual_decimals = max(5, decimals)
        elif value == int(value): actual_decimals = 0
        else: actual_decimals = decimals
        formatted = str(round(float(value), actual_decimals)).replace('.', ',')
        if ',' in formatted:
            integer_part, decimal_part = formatted.split(',')
            if not (abs(value) < 1 and value != 0): decimal_part = decimal_part.ljust(actual_decimals, '0')
            formatted = f"{integer_part},{decimal_part}"
        elif actual_decimals > 0: formatted = f"{formatted},{('0' * actual_decimals)}"
        return formatted

    def format_date(self, date) -> str:
        if isinstance(date, str):
            try: date = datetime.strptime(date, "%Y-%m-%d")
            except: return date
        if isinstance(date, datetime): return date.strftime("%d.%m.%Y")
        return str(date)

    def format_currency(self, value: Decimal) -> str:
        if value is None: return "0,00"
        formatted = str(round(float(value), 2)).replace('.', ',')
        if ',' in formatted:
            integer_part, decimal_part = formatted.split(',')
            formatted = f"{integer_part},{decimal_part.ljust(2, '0')}"
        else: formatted = f"{formatted},00"
        return formatted

    def create_title_page(self, tax_year: Optional[int] = None) -> List[Any]:
        elements = []
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph("Szczegolowy raport podatkowy - Trading212", self.styles['ReportTitle']))
        elements.append(Spacer(1, 0.5*cm))
        subtitle = "Rozliczenie sprzedazy akcji i dywidend"
        if tax_year: subtitle += f" {tax_year}"
        elements.append(Paragraph(subtitle, self.styles['ReportTitle']))
        elements.append(Spacer(1, 2*cm))

        fullname = self.personal_data.get('FULLNAME', 'UZUPELNIJ IMIE I NAZWISKO')
        pesel = self.personal_data.get('PESEL', 'UZUPELNIJ PESEL')
        address = self.personal_data.get('ADDRESS', 'UZUPELNIJ ADRES')
        city = self.personal_data.get('CITY', 'UZUPELNIJ MIASTO')
        postal_code = self.personal_data.get('POSTAL_CODE', 'UZUPELNIJ KOD POCZTOWY')
        tax_office = self.personal_data.get('TAX_OFFICE', 'UZUPELNIJ URZAD SKARBOWY')

        personal_data = [["Imie i nazwisko:", fullname], ["PESEL:", pesel], ["Adres:", address],
            ["", f"{postal_code} {city}"], ["Urzad skarbowy:", tax_office]]
        personal_table = Table(personal_data, colWidths=[4*cm, 10*cm])
        personal_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10), ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        elements.append(personal_table)
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(f"Rok podatkowy: {tax_year}" if tax_year else "Rok podatkowy: Wszystkie lata", self.styles['ReportBodyText']))
        elements.append(Spacer(1, 4*cm))
        elements.append(Paragraph("Dokument wygenerowany automatycznie przez program Trading212 Tax Calculator", self.styles['ReportBodyText']))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Wersja: 1.2.0", self.styles['ReportBodyText']))
        elements.append(PageBreak())
        return elements

    def create_fifo_section(self, fifo_result: FifoCalculationResult) -> List[Any]:
        elements = []
        elements.append(Paragraph("1. Rozliczenie transakcji - metoda FIFO", self.styles['ReportChapter']))
        elements.append(Paragraph("Ponizej przedstawiono rozliczenie transakcji sprzedazy akcji metoda FIFO.", self.styles['ReportBodyText']))

        col_widths = [2.0*cm, 1.5*cm, 3.5*cm, 1.2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2.0*cm, 2.0*cm, 1.8*cm]
        table_style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name), ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), self.base_font_name), ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])])

        # Buy transactions
        buy_transactions = {}
        for match in fifo_result.matches:
            buy_key = (match.buy_transaction.ticker, match.buy_date)
            if buy_key not in buy_transactions: buy_transactions[buy_key] = match.buy_transaction

        if buy_transactions:
            elements.append(Paragraph("1.1 Transakcje zakupu", self.styles['ReportSection']))
            buy_header = [self._create_wrapped_header_cell(h) for h in ["Data", "Ticker", "Nazwa", "Ilosc", "Cena", "Waluta", "Kurs NBP", "Wartosc waluta", "Wartosc PLN", "Oplaty PLN"]]
            buy_data = [buy_header]
            for (ticker, date), tx in sorted(buy_transactions.items(), key=lambda x: x[0][1]):
                ex_rate = self.format_decimal(tx.exchange_rate, 5) if tx.currency == 'GBX' else self.format_decimal(tx.exchange_rate)
                buy_data.append([self.format_date(date), ticker, (tx.name or '')[:20], self.format_decimal(tx.quantity),
                    self.format_decimal(tx.price_per_share, 2), tx.currency, ex_rate,
                    self.format_currency(tx.total_value_foreign), self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal('0'))])
            buy_table = Table(buy_data, colWidths=col_widths, repeatRows=1)
            buy_table.setStyle(table_style)
            elements.append(buy_table)
        else:
            elements.append(Paragraph("1.1 Transakcje zakupu - Brak", self.styles['ReportSection']))

        # Sell transactions
        sell_transactions = {}
        for match in fifo_result.matches:
            sell_key = (match.sell_transaction.ticker, match.sell_date)
            if sell_key not in sell_transactions: sell_transactions[sell_key] = match.sell_transaction

        if sell_transactions:
            elements.append(Paragraph("1.2 Transakcje sprzedazy", self.styles['ReportSection']))
            sell_header = [self._create_wrapped_header_cell(h) for h in ["Data", "Ticker", "Nazwa", "Ilosc", "Cena", "Waluta", "Kurs NBP", "Wartosc waluta", "Wartosc PLN", "Oplaty PLN"]]
            sell_data = [sell_header]
            for (ticker, date), tx in sorted(sell_transactions.items(), key=lambda x: x[0][1]):
                ex_rate = self.format_decimal(tx.exchange_rate, 5) if tx.currency == 'GBX' else self.format_decimal(tx.exchange_rate)
                sell_data.append([self.format_date(date), ticker, (tx.name or '')[:20], self.format_decimal(tx.quantity),
                    self.format_decimal(tx.price_per_share, 2), tx.currency, ex_rate,
                    self.format_currency(tx.total_value_foreign), self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.fees_pln or Decimal('0'))])
            sell_table = Table(sell_data, colWidths=col_widths, repeatRows=1)
            sell_table.setStyle(table_style)
            elements.append(sell_table)
        else:
            elements.append(Paragraph("1.2 Transakcje sprzedazy - Brak", self.styles['ReportSection']))

        # FIFO matches
        if fifo_result.matches:
            elements.append(Paragraph("1.3 Rozliczenie transakcji metoda FIFO", self.styles['ReportSection']))
            match_header = [self._create_wrapped_header_cell(h) for h in ["Ticker", "Data zakupu", "Data sprzedazy", "Liczba akcji", "Przychod PLN", "Koszt PLN", "Dochod/Strata PLN", "% zysku/straty", "Kraj"]]
            match_col_widths = [1.5*cm, 2.0*cm, 2.0*cm, 1.5*cm, 2.0*cm, 2.0*cm, 2.0*cm, 2.0*cm, 3.0*cm]
            matches_data = [match_header]
            for match in sorted(fifo_result.matches, key=lambda m: (m.sell_date, m.ticker)):
                profit_pct = (match.profit_loss_pln / match.cost_pln) * 100 if match.cost_pln > 0 else 0
                matches_data.append([match.ticker, self.format_date(match.buy_date), self.format_date(match.sell_date),
                    self.format_decimal(match.used_quantity), self.format_currency(match.income_pln),
                    self.format_currency(match.cost_pln), self.format_currency(match.profit_loss_pln),
                    f"{self.format_decimal(profit_pct, 2)}%", match.country])
            matches_table = Table(matches_data, colWidths=match_col_widths, repeatRows=1)
            matches_table.setStyle(table_style)
            elements.append(matches_table)

        # Transaction details
        elements.extend(self._create_transaction_details(fifo_result))

        # Summary
        elements.append(Paragraph("1.5 Podsumowanie FIFO", self.styles['ReportSection']))
        total_income = sum(m.income_pln for m in fifo_result.matches)
        total_cost = sum(m.cost_pln for m in fifo_result.matches)
        total_profit = sum(m.profit_loss_pln for m in fifo_result.matches if m.profit_loss_pln > 0)
        total_loss = sum(abs(m.profit_loss_pln) for m in fifo_result.matches if m.profit_loss_pln < 0)
        tax_base = int(max(0, total_profit - total_loss))
        tax_due = int(tax_base * Decimal('0.19'))
        summary_data = [["Pozycja", "Wartosc (PLN)"], ["Laczny przychod", self.format_currency(total_income)],
            ["Laczny koszt uzyskania przychodu", self.format_currency(total_cost)],
            ["Laczny dochod", self.format_currency(total_profit)], ["Laczna strata", self.format_currency(total_loss)],
            ["Podstawa opodatkowania", str(tax_base)], ["Podatek nalezny (19%)", str(tax_due)]]
        summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
        summary_table.setStyle(self.summary_table_style)
        elements.append(summary_table)
        elements.append(PageBreak())
        return elements

    def _create_transaction_details(self, fifo_result: FifoCalculationResult) -> List[Any]:
        elements = []
        elements.append(Paragraph("1.4 Szczegoly transakcji", self.styles['ReportSection']))

        sell_transactions = {}
        for match in fifo_result.matches:
            sell_key = (match.sell_transaction.ticker, match.sell_date)
            if sell_key not in sell_transactions: sell_transactions[sell_key] = []
            sell_transactions[sell_key].append(match)

        for section_idx, (sell_key, matches) in enumerate(sorted(sell_transactions.items(), key=lambda x: (x[0][1], x[0][0])), 1):
            ticker, sell_date = sell_key
            sell_tx = matches[0].sell_transaction
            elements.append(Paragraph(f"1.4.{section_idx} {ticker} ({self.format_date(sell_date)})", self.styles['ReportBodyText']))

            tx_details = [["Ticker:", ticker], ["Nazwa:", (sell_tx.name or '')[:30]],
                ["Data sprzedazy:", self.format_date(sell_date)],
                ["Ilosc sprzedanych akcji:", self.format_decimal(sell_tx.quantity)],
                ["Cena sprzedazy:", f"{self.format_decimal(sell_tx.price_per_share)} {sell_tx.currency}"],
                ["Kurs NBP:", self.format_decimal(sell_tx.exchange_rate)],
                ["Wartosc w PLN:", f"{self.format_currency(sell_tx.total_value_pln)} PLN"]]
            tx_table = Table(tx_details, colWidths=[5*cm, 10*cm])
            tx_table.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), self.bold_font_name),
                ('FONTNAME', (1, 0), (1, -1), self.base_font_name), ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'), ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)]))
            elements.append(tx_table)
            elements.append(Spacer(1, 0.3*cm))

            elements.append(Paragraph("Dopasowane transakcje zakupu:", self.styles['ReportBodyText']))
            for idx, match in enumerate(sorted(matches, key=lambda m: m.buy_date), 1):
                buy_tx = match.buy_transaction
                buy_details = [[f"Zakup #{idx}", ""], ["Data zakupu:", self.format_date(match.buy_date)],
                    ["Ilosc dopasowanych akcji:", self.format_decimal(match.used_quantity)],
                    ["Cena zakupu:", f"{self.format_decimal(buy_tx.price_per_share)} {buy_tx.currency}"],
                    ["Wartosc zakupu w PLN:", f"{self.format_currency(match.buy_price_pln)} PLN"]]
                buy_table = Table(buy_details, colWidths=[5*cm, 8*cm])
                buy_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), self.base_font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 8), ('SPAN', (0, 0), (1, 0)),
                    ('FONTNAME', (0, 0), (1, 0), self.bold_font_name), ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                    ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey), ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey)]))
                elements.append(buy_table)
                elements.append(Spacer(1, 0.2*cm))

            total_income = sum(m.income_pln for m in matches)
            total_cost = sum(m.cost_pln for m in matches)
            profit_loss = total_income - total_cost
            profit_pct = (profit_loss / total_cost * 100) if total_cost > 0 else 0
            summary = [["Przychod (PLN):", self.format_currency(total_income)],
                ["Koszt (PLN):", self.format_currency(total_cost)],
                ["Dochod/Strata (PLN):", self.format_currency(profit_loss)],
                ["% zysku/straty:", f"{self.format_decimal(profit_pct, 2)}%"]]
            summary_table = Table(summary, colWidths=[5*cm, 8*cm])
            summary_table.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), self.bold_font_name),
                ('FONTNAME', (1, 0), (1, -1), self.base_font_name), ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.8*cm))

        return elements

    def create_dividend_section(self, dividend_result: DividendCalculationResult) -> List[Any]:
        elements = []
        elements.append(Paragraph("2. Rozliczenie dywidend", self.styles['ReportChapter']))

        if not dividend_result.summaries:
            elements.append(Paragraph("Brak dywidend do rozliczenia.", self.styles['ReportBodyText']))
            elements.append(PageBreak())
            return elements

        elements.append(Paragraph("2.1 Podsumowanie dywidend wg kraju", self.styles['ReportSection']))
        summary_header = [self._create_wrapped_header_cell(h) for h in ["Panstwo", "UPO", "Dywidenda PLN", "Podatek pobrany PLN", "Podatek PL 19%", "Do zaplaty PL"]]
        summary_data = [summary_header]
        total_dividend = total_tax_abroad = total_tax_poland = total_tax_to_pay = Decimal('0')

        for country, summary in sorted(dividend_result.summaries.items()):
            # Check if country has tax treaty
            treaty_status = "TAK" if summary.has_tax_treaty else "NIE"
            summary_data.append([country, treaty_status, self.format_currency(summary.total_dividend_pln),
                self.format_currency(summary.tax_paid_abroad_pln), self.format_currency(summary.tax_due_poland),
                self.format_currency(summary.tax_to_pay)])
            total_dividend += summary.total_dividend_pln
            total_tax_abroad += summary.tax_paid_abroad_pln
            total_tax_poland += summary.tax_due_poland
            total_tax_to_pay += summary.tax_to_pay

        summary_data.append(["RAZEM", "", self.format_currency(total_dividend), self.format_currency(total_tax_abroad),
            self.format_currency(total_tax_poland), self.format_currency(total_tax_to_pay)])

        summary_table = Table(summary_data, colWidths=[3.5*cm, 1.5*cm, 3.0*cm, 3.0*cm, 3.0*cm, 3.0*cm], repeatRows=1)
        summary_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name), ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), ('FONTNAME', (0, -1), (-1, -1), self.bold_font_name),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*cm))

        # Add explanation about tax treaties
        elements.append(Paragraph("Uwaga o umowach UPO:", self.styles['ReportBodyText']))
        elements.append(Paragraph("• UPO = TAK: Kraj ma umowę o unikaniu podwójnego opodatkowania z Polską. Podatek zapłacony za granicą jest odliczany od podatku w PL.", self.styles['ReportBodyText']))
        elements.append(Paragraph("• UPO = NIE: Kraj NIE ma umowy z Polską. Pełne 19% podatku należy zapłacić w PL, niezależnie od podatku zapłaconego za granicą.", self.styles['ReportBodyText']))
        elements.append(Spacer(1, 0.5*cm))

        for country_idx, (country, summary) in enumerate(sorted(dividend_result.summaries.items()), 1):
            elements.append(Paragraph(f"2.{country_idx + 1} Dywidendy - {country}", self.styles['ReportSection']))
            div_header = [self._create_wrapped_header_cell(h) for h in ["Data", "Ticker", "Nazwa", "Ilosc", "Dyw/akcje", "Waluta", "Kurs NBP", "Wart. waluta", "Wart. PLN", "Pod. pobrany", "Pod. PLN"]]
            div_col_widths = [1.8*cm, 1.3*cm, 2.5*cm, 1.0*cm, 1.7*cm, 1.2*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.7*cm, 1.7*cm]
            div_data = [div_header]

            for tx in sorted(summary.transactions, key=lambda t: t.date):
                ex_rate = self.format_decimal(tx.exchange_rate, 5) if tx.currency == 'GBX' else self.format_decimal(tx.exchange_rate)
                div_data.append([self.format_date(tx.date), tx.ticker, (tx.name or '')[:20],
                    self.format_decimal(tx.quantity), self.format_decimal(tx.price_per_share, 4), tx.currency,
                    ex_rate, self.format_currency(tx.total_value_foreign), self.format_currency(tx.total_value_pln),
                    self.format_currency(tx.withholding_tax_foreign or Decimal('0')),
                    self.format_currency(tx.withholding_tax_pln or Decimal('0'))])

            div_table = Table(div_data, colWidths=div_col_widths, repeatRows=1)
            div_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name), ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'), ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])]))
            elements.append(div_table)

            cs_data = [["Suma dywidend", self.format_currency(summary.total_dividend_pln)],
                ["Podatek pobrany", self.format_currency(summary.tax_paid_abroad_pln)],
                ["Podatek PL (19%)", self.format_currency(summary.tax_due_poland)],
                ["Do zaplaty w PL", self.format_currency(summary.tax_to_pay)]]
            cs_table = Table(cs_data, colWidths=[6*cm, 3*cm])
            cs_table.setStyle(self.summary_table_style)
            elements.append(cs_table)
            elements.append(Spacer(1, 0.5*cm))

        elements.append(PageBreak())
        return elements

    def create_interest_section(self, interest_result: InterestCalculationResult) -> List[Any]:
        elements = []
        elements.append(Paragraph("3. Odsetki od srodkow pienieznych", self.styles['ReportChapter']))

        if not interest_result or interest_result.total_interest_pln <= 0:
            elements.append(Paragraph("Brak odsetek do rozliczenia.", self.styles['ReportBodyText']))
            elements.append(PageBreak())
            return elements

        elements.append(Paragraph("3.1 Podsumowanie odsetek", self.styles['ReportSection']))
        summary_data = [["Pozycja", "Wartosc"],
            ["Laczne odsetki (PLN)", self.format_currency(interest_result.total_interest_pln)],
            ["Podatek nalezny (19%)", self.format_currency(interest_result.total_tax_due)]]

        for currency, summary in interest_result.summaries.items():
            summary_data.append([f"Odsetki w walucie {currency}",
                f"{self.format_currency(summary.total_interest_foreign)} {currency} = {self.format_currency(summary.total_interest_pln)} PLN"])

        summary_table = Table(summary_data, colWidths=[8*cm, 7*cm])
        summary_table.setStyle(self.summary_table_style)
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Uwaga: Odsetki podlegaja opodatkowaniu zryczaltowanym podatkiem dochodowym 19%.", self.styles['ReportBodyText']))
        elements.append(PageBreak())
        return elements

    def create_tax_forms_section(self, fifo_result: FifoCalculationResult, dividend_result: DividendCalculationResult,
                                 interest_result: Optional[InterestCalculationResult] = None) -> List[Any]:
        elements = []
        elements.append(Paragraph("4. Dane do formularzy podatkowych", self.styles['ReportChapter']))

        # Calculate FIFO totals
        fifo_df = fifo_result.to_dataframe()
        total_income = total_cost = profit = loss = Decimal('0')
        if not fifo_df.empty:
            total_income = sum(m.income_pln for m in fifo_result.matches)
            total_cost = sum(m.cost_pln for m in fifo_result.matches)
            if total_income > total_cost: profit = total_income - total_cost
            else: loss = total_cost - total_income
        tax_base = int(profit)
        tax_due_fifo = int(tax_base * Decimal('0.19'))

        # Calculate dividend totals
        div_income = div_tax_due = div_tax_paid_abroad = div_tax_to_pay = Decimal('0')
        if dividend_result.summaries:
            for summary in dividend_result.summaries.values():
                div_income += summary.total_dividend_pln
                div_tax_due += summary.tax_due_poland
                div_tax_paid_abroad += summary.tax_paid_abroad_pln
                div_tax_to_pay += summary.tax_to_pay

        # Calculate interest totals
        interest_income = interest_tax_due = Decimal('0')
        if interest_result and interest_result.total_interest_pln > 0:
            interest_income = interest_result.total_interest_pln
            interest_tax_due = interest_result.total_tax_due

        # Section 4.1 - PIT-38 Main Data (including interest)
        elements.append(Paragraph("4.1 Dane do deklaracji PIT-38 - Sekcja C i D", self.styles['ReportSection']))

        pit38_data = [["Pole", "Opis", "Wartosc PLN"],
            ["C.22", "Przychod ze sprzedazy akcji (FIFO)", self.format_currency(total_income)],
            ["C.23", "Koszty uzyskania przychodu (FIFO)", self.format_currency(total_cost)],
            ["C.26", "Dochod (jezeli C.24 > C.25)", self.format_currency(profit)],
            ["C.27", "Strata (jezeli C.24 < C.25)", self.format_currency(loss)],
            ["D.29", "Podstawa obliczenia podatku (z FIFO)", str(tax_base)],
            ["D.31", "Podatek nalezny z akcji (19%)", str(tax_due_fifo)]]

        # Add interest to PIT-38 if present
        if interest_income > 0:
            pit38_data.extend([
                ["---", "--- ODSETKI (dodaj do powyzszych) ---", "---"],
                ["C.22", "+ Przychod z odsetek", self.format_currency(interest_income)],
                ["C.23", "+ Koszty (brak dla odsetek)", "0,00"],
                ["D.29", "+ Podstawa z odsetek", self.format_currency(interest_income)],
                ["D.31", "+ Podatek z odsetek (19%)", self.format_currency(interest_tax_due)]
            ])

        pit38_table = Table(pit38_data, colWidths=[1.5*cm, 8*cm, 3.5*cm])
        pit38_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        elements.append(pit38_table)

        if interest_income > 0:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("Uwaga: Odsetki należy dodać do odpowiednich pól (przychód, podstawa, podatek) w PIT-38.", self.styles['ReportBodyText']))

        elements.append(Spacer(1, 0.5*cm))

        # Section 4.2 - PIT-38 Section G (Dividends)
        if dividend_result.summaries:
            elements.append(Paragraph("4.2 PIT-38 Sekcja G - Dywidendy zagraniczne", self.styles['ReportSection']))
            g_header = [self._create_wrapped_header_cell(h) for h in ["Panstwo", "UPO", "Przychod PLN", "Podatek PL 19%", "Podatek zagr.", "Do zaplaty"]]
            g_data = [g_header]
            for i, (country, summary) in enumerate(sorted(dividend_result.summaries.items()), 1):
                treaty_status = "TAK" if summary.has_tax_treaty else "NIE"
                g_data.append([
                    f"{country}",
                    treaty_status,
                    self.format_currency(summary.total_dividend_pln),
                    self.format_currency(summary.tax_due_poland),
                    self.format_currency(summary.tax_paid_abroad_pln),
                    self.format_currency(summary.tax_to_pay)
                ])
            g_table = Table(g_data, colWidths=[4*cm, 1.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm])
            g_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(g_table)
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("Wypełnij odpowiednie pola G.42-G.71 dla każdego kraju w PIT-38.", self.styles['ReportBodyText']))
            elements.append(Paragraph("UWAGA: Jeśli UPO=NIE, podatek zagraniczny NIE jest odliczany - zapłać pełne 19%!", self.styles['ReportBodyText']))
            elements.append(Spacer(1, 0.5*cm))

        # Section 4.3 - PIT/ZG attachment
        elements.append(Paragraph("4.3 Załącznik PIT/ZG - Źródła przychodów zagranicznych", self.styles['ReportSection']))
        if not fifo_df.empty:
            country_groups = fifo_df.groupby('country')
            pitzg_header = [self._create_wrapped_header_cell(h) for h in ["Panstwo", "Przychod PLN", "Koszty PLN", "Dochod PLN", "Podatek zagr."]]
            pitzg_data = [pitzg_header]
            for country, group in sorted(country_groups):
                sec_income = Decimal(str(group['income_pln'].sum()))
                sec_cost = Decimal(str(group['cost_pln'].sum()))
                sec_profit = max(Decimal('0'), sec_income - sec_cost)
                pitzg_data.append([country, self.format_currency(sec_income), self.format_currency(sec_cost),
                                   self.format_currency(sec_profit), "0,00"])
            pitzg_table = Table(pitzg_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm, 3*cm])
            pitzg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(pitzg_table)
        else:
            elements.append(Paragraph("Brak transakcji sprzedaży do wykazania w załączniku PIT/ZG.", self.styles['ReportBodyText']))

        elements.append(PageBreak())

        # Section 4.4 - FINAL SUMMARY WITH EXACT INSTRUCTIONS
        elements.append(Paragraph("4.4 PODSUMOWANIE - CO GDZIE WPISAĆ", self.styles['ReportSection']))
        elements.append(Paragraph("Poniżej znajdziesz konkretne kwoty do wpisania w poszczególne pola formularzy:", self.styles['ReportBodyText']))
        elements.append(Spacer(1, 0.3*cm))

        # Calculate grand totals
        total_tax_to_pay = tax_due_fifo + div_tax_to_pay + interest_tax_due

        summary_instructions = []
        summary_instructions.append(["FORMULARZ", "POLE", "OPIS", "KWOTA"])

        # PIT-38 Section C
        summary_instructions.append(["PIT-38", "C.22", "Przychód (akcje + odsetki)",
                                     self.format_currency(total_income + interest_income)])
        summary_instructions.append(["PIT-38", "C.23", "Koszty (tylko z akcji)",
                                     self.format_currency(total_cost)])
        if profit > 0:
            summary_instructions.append(["PIT-38", "C.26", "Dochód (jeśli >0)",
                                         self.format_currency(profit + interest_income)])
        if loss > 0:
            summary_instructions.append(["PIT-38", "C.27", "Strata (jeśli <0)",
                                         self.format_currency(loss)])

        # PIT-38 Section D
        summary_instructions.append(["PIT-38", "D.29", "Podstawa opodatkowania",
                                     self.format_currency(Decimal(str(tax_base)) + interest_income)])
        summary_instructions.append(["PIT-38", "D.31", "Podatek 19% (akcje + odsetki)",
                                     self.format_currency(Decimal(str(tax_due_fifo)) + interest_tax_due)])

        # PIT-38 Section G (Dividends)
        if dividend_result.summaries:
            summary_instructions.append(["---", "---", "--- DYWIDENDY ---", "---"])
            for i, (country, summary) in enumerate(sorted(dividend_result.summaries.items()), 1):
                field_num = 42 + (i-1) * 5
                treaty_note = " [UPO: TAK]" if summary.has_tax_treaty else " [BRAK UPO!]"
                summary_instructions.append([
                    "PIT-38",
                    f"G.{field_num}-{field_num+4}",
                    f"Dywidendy {country}{treaty_note}",
                    self.format_currency(summary.tax_to_pay)
                ])

        # Grand total
        summary_instructions.append(["---", "---", "---", "---"])
        summary_instructions.append(["RAZEM", "D.31 + G", "CAŁKOWITY PODATEK DO ZAPŁATY",
                                     f"{self.format_currency(total_tax_to_pay)} PLN"])

        summary_table = Table(summary_instructions, colWidths=[2.5*cm, 2.5*cm, 7*cm, 3*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), self.bold_font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), self.bold_font_name),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(summary_table)

        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("WAŻNE PRZYPOMNIENIA:", self.styles['ReportSection']))
        elements.append(Paragraph("• Załącz formularz PIT/ZG do PIT-38 (źródła zagraniczne)", self.styles['ReportBodyText']))
        elements.append(Paragraph("• Dla krajów BEZ umowy UPO: płacisz pełne 19% podatku w Polsce!", self.styles['ReportBodyText']))
        elements.append(Paragraph("• Odsetki zostały JUŻ UWZGLĘDNIONE w polach C.22, D.29 i D.31", self.styles['ReportBodyText']))
        elements.append(Paragraph("• Sprawdź dokładnie kwoty przed wysłaniem deklaracji", self.styles['ReportBodyText']))

        return elements

    def export(self, data: Dict[str, Any], output_path: str) -> bool:
        try:
            self.logger.info(f"Using font: {self.base_font_name}")
            tax_year = data.get('tax_year')
            fifo_result = data.get('fifo_result')
            dividend_result = data.get('dividend_result')
            interest_result = data.get('interest_result')

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
            doc.title = "Trading212 Tax Calculator Report"
            doc.author = "Trading212 Tax Calculator"

            elements = []
            elements.extend(self.create_title_page(tax_year))
            elements.extend(self.create_fifo_section(fifo_result))
            elements.extend(self.create_dividend_section(dividend_result))
            if interest_result:
                elements.extend(self.create_interest_section(interest_result))
            elements.extend(self.create_tax_forms_section(fifo_result, dividend_result, interest_result))

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
