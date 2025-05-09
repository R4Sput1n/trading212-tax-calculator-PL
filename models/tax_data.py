from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Any, Optional


@dataclass
class SecurityTransactionTax:
    """Tax data for security transactions"""
    total_income: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    profit: Decimal = Decimal('0')
    loss: Decimal = Decimal('0')
    tax_base: int = 0  # Rounded to full PLN
    tax_due: int = 0  # 19% of tax_base


@dataclass
class DividendTax:
    """Tax data for dividends from a specific country"""
    country: str
    total_dividend: Decimal = Decimal('0')
    tax_paid_abroad: Decimal = Decimal('0')
    tax_due_poland: Decimal = Decimal('0')
    tax_to_pay: Decimal = Decimal('0')
    count: int = 0


@dataclass
class PIT38FormData:
    """Data for PIT-38 tax form"""
    security_tax: SecurityTransactionTax = field(default_factory=SecurityTransactionTax)
    dividend_taxes: Dict[str, DividendTax] = field(default_factory=dict)
    
    @property
    def total_tax_due(self) -> int:
        """Calculate total tax due (securities + dividends)"""
        return self.security_tax.tax_due + sum(
            int(dt.tax_to_pay) for dt in self.dividend_taxes.values()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        result = {
            # Section C - Securities
            "C.22": float(self.security_tax.total_income),
            "C.23": float(self.security_tax.total_cost),
            "C.24": float(self.security_tax.total_income),  # Same as C.22
            "C.25": float(self.security_tax.total_cost),  # Same as C.23
            "C.26": float(self.security_tax.profit),
            "C.27": float(self.security_tax.loss),
            "D.29": self.security_tax.tax_base,
            "D.31": self.security_tax.tax_due,
            "D.33": self.security_tax.tax_due  # Same as D.31
        }
        
        # Section G - Dividends
        for i, (country, tax) in enumerate(sorted(self.dividend_taxes.items()), 1):
            result[f"G.43_{i}"] = country
            result[f"G.44_{i}"] = float(tax.total_dividend)
            result[f"G.45_{i}"] = float(tax.tax_due_poland)
            result[f"G.46_{i}"] = float(tax.tax_paid_abroad)
            result[f"G.47_{i}"] = float(tax.tax_to_pay)
        
        return result


@dataclass
class CountryIncome:
    """Income from a specific country for PIT/ZG form"""
    country: str
    income_type: str  # e.g., "10" for securities
    income: Decimal = Decimal('0')
    cost: Decimal = Decimal('0')
    profit: Decimal = Decimal('0')
    tax_paid_abroad: Decimal = Decimal('0')
    requires_verification: bool = False
    include_in_official_form: bool = False


@dataclass
class PITZGFormData:
    """Data for PIT/ZG tax form (income from foreign sources)"""
    country_incomes: Dict[str, CountryIncome] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        result = {}
        
        for i, (country, income) in enumerate(sorted(self.country_incomes.items()), 1):
            result[f"kraj_{i}"] = country
            result[f"kod_{i}"] = income.income_type
            result[f"przychód_{i}"] = float(income.income)
            result[f"koszt_{i}"] = float(income.cost)
            result[f"dochód_{i}"] = float(income.profit)
            result[f"podatek_{i}"] = float(income.tax_paid_abroad)
        
        return result


@dataclass
class TaxReport:
    """Complete tax report data"""
    pit38: PIT38FormData = field(default_factory=PIT38FormData)
    pitzg: PITZGFormData = field(default_factory=PITZGFormData)
    year: int = field(default_factory=lambda: __import__('datetime').datetime.now().year - 1)
    
    # Additional metadata
    transaction_count: int = 0
    dividend_count: int = 0
    countries: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
