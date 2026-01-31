"""
Dividend Calculator for Polish tax reporting.
Calculates dividend income and withholding tax credits by country.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from calculators.calculator_interface import CalculatorInterface
from models.transaction import DividendTransaction, Transaction

logger = logging.getLogger(__name__)


@dataclass
class DividendSummary:
    """Summary of dividends for a specific country."""

    country: str
    total_dividend_pln: Decimal = Decimal("0")
    tax_paid_abroad_pln: Decimal = Decimal("0")
    tax_due_poland: Decimal = Decimal("0")
    tax_to_pay: Decimal = Decimal("0")
    transactions: List[DividendTransaction] = field(default_factory=list)


@dataclass
class DividendCalculationResult:
    """Result of dividend calculation."""

    summaries: Dict[str, DividendSummary] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to a pandas DataFrame."""
        data = []
        for country, summary in self.summaries.items():
            for tx in summary.transactions:
                data.append(
                    {
                        "date": tx.date,
                        "ticker": tx.ticker,
                        "name": tx.name,
                        "country": country,
                        "quantity": tx.quantity,
                        "dividend_per_share": tx.price_per_share,
                        "currency": tx.currency,
                        "exchange_rate": tx.exchange_rate,
                        "total_value_foreign": tx.total_value_foreign,
                        "total_value_pln": tx.total_value_pln,
                        "withholding_tax_foreign": tx.withholding_tax_foreign,
                        "withholding_tax_pln": tx.withholding_tax_pln,
                    }
                )
        return pd.DataFrame(data)


class DividendCalculator(CalculatorInterface[List[Transaction], DividendCalculationResult]):
    """Calculator for dividend income and withholding tax."""

    def __init__(self, tax_rate: Decimal = Decimal("0.19")):
        """
        Initialize the dividend calculator.

        Args:
            tax_rate: Polish tax rate (default 19%)
        """
        self.tax_rate = tax_rate

    def validate(self, transactions: List[Transaction]) -> List[str]:
        """
        Validate dividend transactions.

        Args:
            transactions: List of transactions to validate

        Returns:
            List of validation issues
        """
        issues = []
        dividend_transactions = [tx for tx in transactions if isinstance(tx, DividendTransaction)]

        for i, tx in enumerate(dividend_transactions):
            if tx.quantity <= 0:
                issues.append(f"Dividend #{i} ({tx.ticker}) has invalid quantity: {tx.quantity}")
            if not tx.country:
                issues.append(f"Dividend #{i} ({tx.ticker}) has no country information")
            if tx.total_value_pln is None or tx.total_value_pln <= 0:
                issues.append(
                    f"Dividend #{i} ({tx.ticker}) has invalid PLN value: {tx.total_value_pln}"
                )

        return issues

    def calculate(
        self, transactions: List[Transaction], tax_year: Optional[int] = None
    ) -> DividendCalculationResult:
        """
        Calculate dividend summaries by country.

        Args:
            transactions: List of all transactions
            tax_year: Optional tax year to filter by

        Returns:
            DividendCalculationResult with summaries by country
        """
        issues = []

        # Filter to dividend transactions only
        dividend_transactions = [tx for tx in transactions if isinstance(tx, DividendTransaction)]
        logger.info(
            f"Dividend Calculator: {len(dividend_transactions)} dividend transactions found"
        )

        # Filter by year if specified
        if tax_year:
            original_count = len(dividend_transactions)
            dividend_transactions = [tx for tx in dividend_transactions if tx.date.year == tax_year]
            logger.info(
                f"After year filter ({tax_year}): {len(dividend_transactions)} of {original_count} dividends"
            )

        # Validate and collect issues (but don't skip transactions)
        issues = self.validate(dividend_transactions)

        # Group by country
        summaries: Dict[str, DividendSummary] = {}

        for i, tx in enumerate(dividend_transactions):
            # Determine country (use fallback if missing)
            country = tx.country if tx.country else "Nieznany"

            # Get PLN values (use 0 if missing)
            dividend_pln = tx.total_value_pln if tx.total_value_pln else Decimal("0")
            withholding_pln = tx.withholding_tax_pln if tx.withholding_tax_pln else Decimal("0")

            # Skip if no actual dividend value
            if dividend_pln <= 0:
                logger.debug(f"Skipping dividend #{i} ({tx.ticker}): no PLN value")
                continue

            # Create or update summary for this country
            if country not in summaries:
                summaries[country] = DividendSummary(country=country)

            summary = summaries[country]
            summary.total_dividend_pln += dividend_pln
            summary.tax_paid_abroad_pln += withholding_pln
            summary.transactions.append(tx)

            logger.debug(
                f"Added dividend #{i}: {tx.ticker} ({country}), "
                f"value={dividend_pln} PLN, tax={withholding_pln} PLN"
            )

        # Calculate tax due for each country
        for country, summary in summaries.items():
            summary.tax_due_poland = summary.total_dividend_pln * self.tax_rate
            summary.tax_to_pay = max(
                Decimal("0"), summary.tax_due_poland - summary.tax_paid_abroad_pln
            )
            logger.info(
                f"Country '{country}': {len(summary.transactions)} dividends, "
                f"total={summary.total_dividend_pln:.2f} PLN, "
                f"tax_abroad={summary.tax_paid_abroad_pln:.2f} PLN, "
                f"tax_to_pay={summary.tax_to_pay:.2f} PLN"
            )

        # Build stats
        stats = {
            "total_dividends": len(dividend_transactions),
            "total_dividend_pln": sum(s.total_dividend_pln for s in summaries.values()),
            "total_tax_paid_abroad": sum(s.tax_paid_abroad_pln for s in summaries.values()),
            "total_tax_to_pay": sum(s.tax_to_pay for s in summaries.values()),
            "countries": list(summaries.keys()),
        }

        logger.info(
            f"Dividend calculation complete: {len(summaries)} countries, "
            f"total={stats['total_dividend_pln']:.2f} PLN"
        )

        return DividendCalculationResult(summaries=summaries, stats=stats, issues=issues)
