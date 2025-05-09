from typing import Dict, Any, List, Tuple
from decimal import Decimal
import pandas as pd
from dataclasses import dataclass

from calculators.fifo_calculator import FifoCalculationResult
from calculators.dividend_calculator import DividendCalculationResult
from exporters.exporter_interface import ExporterInterface


@dataclass
class PIT38Summary:
    """Summary of data for PIT-38 tax form"""
    # Section C - Securities transactions
    total_income: Decimal
    total_cost: Decimal
    profit: Decimal
    loss: Decimal
    tax_base: int  # rounded to full PLN
    tax_due: int  # 19% of tax_base
    
    # Section G - Dividends
    dividend_data: List[Dict[str, Any]]
    
    def get_all_fields(self) -> Dict[str, Any]:
        """Get all fields for the tax form as a dictionary"""
        fields = {
            "C.22": float(self.total_income),
            "C.23": float(self.total_cost),
            "C.24": float(self.total_income),  # Same as C.22
            "C.25": float(self.total_cost),  # Same as C.23
            "C.26": float(self.profit),
            "C.27": float(self.loss),
            "D.29": self.tax_base,
            "D.31": self.tax_due,
            "D.33": self.tax_due  # Same as D.31
        }
        
        # Add dividend data
        for i, div_data in enumerate(self.dividend_data, 1):
            fields[f"G.43_{i}"] = div_data["country"]
            fields[f"G.44_{i}"] = float(div_data["dividend_amount"])
            fields[f"G.45_{i}"] = float(div_data["tax_due"])
            fields[f"G.46_{i}"] = float(div_data["tax_paid_abroad"])
            fields[f"G.47_{i}"] = float(div_data["tax_to_pay"])
        
        return fields


@dataclass
class PITZGData:
    """Data for PIT/ZG tax form (income from foreign sources)"""
    country: str
    include_in_official_form: bool
    requires_verification: bool
    securities_income: Decimal
    securities_cost: Decimal
    securities_profit: Decimal
    tax_paid_abroad: Decimal


@dataclass
class TaxFormData:
    """Combined data for all tax forms"""
    pit38: PIT38Summary
    pitzg: List[PITZGData]


class TaxFormExporter(ExporterInterface[TaxFormData]):
    """Exporter for tax form data"""
    
    def export(self, data: TaxFormData, output_path: str) -> bool:
        """
        Export tax form data to an Excel file with separate sheets.
        
        Args:
            data: Tax form data to export
            output_path: Path to the output Excel file
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # PIT-38 - Securities transactions
                self._export_pit38_securities(data.pit38, writer)
                
                # PIT-38 - Dividends
                self._export_pit38_dividends(data.pit38, writer)
                
                # PIT/ZG
                self._export_pitzg(data.pitzg, writer)
            
            return True
        except Exception as e:
            print(f"Error exporting tax form data: {e}")
            return False
    
    def _export_pit38_securities(self, pit38: PIT38Summary, writer) -> None:
        """Export PIT-38 securities data to Excel worksheet"""
        securities_data = [
            {"KOMÓRKA": "C.22", "NAZWA": "Inne przychody / Przychód", "WARTOŚĆ": float(pit38.total_income)},
            {"KOMÓRKA": "C.23", "NAZWA": "Inne przychody / Koszty uzyskania przychodów", 
             "WARTOŚĆ": float(pit38.total_cost)},
            {"KOMÓRKA": "C.24", "NAZWA": "Razem (suma kwot z wierszy 1 do 2) / Przychód",
             "WARTOŚĆ": float(pit38.total_income)},
            {"KOMÓRKA": "C.25", "NAZWA": "Razem (suma kwot z wierszy 1 do 2) / Koszty uzyskania przychodów",
             "WARTOŚĆ": float(pit38.total_cost)},
            {"KOMÓRKA": "C.26", "NAZWA": "Dochód (b-c)", "WARTOŚĆ": float(pit38.profit)},
            {"KOMÓRKA": "C.27", "NAZWA": "Strata (b-c)", "WARTOŚĆ": float(pit38.loss)},
            {"KOMÓRKA": "D.29", "NAZWA": "Podstawa obliczenia podatku (po zaokrągleniu do pełych złotch)",
             "WARTOŚĆ": pit38.tax_base},
            {"KOMÓRKA": "D.31", "NAZWA": "Podatek dochodowy o którym mowa w art. 30b ustawy",
             "WARTOŚĆ": pit38.tax_due},
            {"KOMÓRKA": "D.33", "NAZWA": "Podatek należny (po zaokrągleniu do pełnych złotych)",
             "WARTOŚĆ": pit38.tax_due}
        ]
        
        pd.DataFrame(securities_data).to_excel(writer, sheet_name='PIT-38 - Akcje i Koszty', index=False)
    
    def _export_pit38_dividends(self, pit38: PIT38Summary, writer) -> None:
        """Export PIT-38 dividend data to Excel worksheet"""
        # Calculate total dividend amount
        total_dividend_amount = sum(Decimal(str(d["dividend_amount"])) for d in pit38.dividend_data)
        
        dividend_data = [
            {
                "KOMÓRKA": "-",
                "NAZWA": "Suma wypłat dywidend zagranicznych - podstawa opodatkowania (wiersz pomocniczy)",
                "WARTOŚĆ": float(total_dividend_amount)
            }
        ]
        
        # Add data for each country
        for i, div in enumerate(pit38.dividend_data, 1):
            country = div["country"]
            tax_due = Decimal(str(div["tax_due"]))
            tax_paid = Decimal(str(div["tax_paid_abroad"]))
            tax_to_pay = Decimal(str(div["tax_to_pay"]))
            
            dividend_data.append({
                "KOMÓRKA": "G.45",
                "NAZWA": "Zryczałtowany podatek obliczony od przychodów (dochodów), o których mowa w art. 30a ust. 1 pkt 1–5 ustawy, uzyskanych poza granicami Rzeczypospolitej Polskiej",
                "WARTOŚĆ": float(tax_due)
            })
            
            dividend_data.append({
                "KOMÓRKA": "G.46",
                "NAZWA": "Podatek zapłacony za granicą, o którym mowa w art. 30a ust. 9 ustawy (przeliczony na złote)",
                "WARTOŚĆ": float(tax_paid)
            })
            
            dividend_data.append({
                "KOMÓRKA": "-",
                "NAZWA": "Dokładna wartość podatku do dopłacenia (wiersz pomocniczy)",
                "WARTOŚĆ": float(tax_due - tax_paid)
            })
            
            dividend_data.append({
                "KOMÓRKA": "G.47",
                "NAZWA": "Różnica między zryczałtowanym podatkiem a podatkiem zapłaconym za granicą",
                "WARTOŚĆ": float(tax_to_pay)
            })
        
        pd.DataFrame(dividend_data).to_excel(writer, sheet_name='PIT-38 - Dywidendy', index=False)
    
    def _export_pitzg(self, pitzg_data: List[PITZGData], writer) -> None:
        """Export PIT/ZG data to Excel worksheet"""
        data = []
        
        for entry in pitzg_data:
            data.append({
                "PAŃSTWO UZYSKANIA PRZYCHODU": entry.country,
                "KOD KRAJU": "",
                "UWZGLĘDNIĆ W OFICJALNYM PIT/ZG": "TAK" if entry.include_in_official_form else "NIE",
                "WYMAGA WERYFIKACJI": "TAK" if entry.requires_verification else "NIE",
                "PRZYCHÓD [PLN]": float(entry.securities_income),
                "KOSZT UZYSKANIA PRZYCHODU [PLN]": float(entry.securities_cost),
                "BILANS [PLN]": float(entry.securities_profit),
                "PODATEK ZAPŁACONY ZA GRANICĄ [PLN]": float(entry.tax_paid_abroad)
            })
        
        pd.DataFrame(data).to_excel(writer, sheet_name='PIT-ZG', index=False)


class TaxFormGenerator:
    """Generator for tax form data"""
    
    def __init__(self, tax_rate: float = 0.19):
        """
        Initialize TaxFormGenerator.
        
        Args:
            tax_rate: Tax rate for income in Poland (default: 19%)
        """
        self.tax_rate = Decimal(str(tax_rate))
    
    def generate_tax_forms(
        self, 
        fifo_result: FifoCalculationResult, 
        dividend_result: DividendCalculationResult
    ) -> TaxFormData:
        """
        Generate tax form data from calculation results.
        
        Args:
            fifo_result: Result of FIFO calculation
            dividend_result: Result of dividend calculation
            
        Returns:
            TaxFormData with data for PIT-38 and PIT/ZG forms
        """
        # Generate PIT-38 summary
        pit38 = self._generate_pit38_summary(fifo_result, dividend_result)
        
        # Generate PIT/ZG data
        pitzg = self._generate_pitzg_data(fifo_result, dividend_result)
        
        return TaxFormData(pit38=pit38, pitzg=pitzg)
    
    def _generate_pit38_summary(
        self, 
        fifo_result: FifoCalculationResult, 
        dividend_result: DividendCalculationResult
    ) -> PIT38Summary:
        """Generate PIT-38 summary from calculation results"""
        # Calculate securities totals
        fifo_df = fifo_result.to_dataframe()
        
        total_income = Decimal('0')
        total_cost = Decimal('0')
        profit = Decimal('0')
        loss = Decimal('0')
        
        if not fifo_df.empty:
            total_income = Decimal(str(fifo_df['income_pln'].sum()))
            total_cost = Decimal(str(fifo_df['cost_pln'].sum()))
            
            if total_income > total_cost:
                profit = total_income - total_cost
                loss = Decimal('0')
            else:
                profit = Decimal('0')
                loss = total_cost - total_income
        
        # Calculate tax base and due (rounded to full PLN)
        tax_base = int(profit)
        tax_due = int(tax_base * self.tax_rate)
        
        # Prepare dividend data
        dividend_data = []
        
        for country, summary in dividend_result.summaries.items():
            dividend_data.append({
                "country": country,
                "dividend_amount": summary.total_dividend_pln,
                "tax_due": summary.tax_due_poland,
                "tax_paid_abroad": summary.tax_paid_abroad_pln,
                "tax_to_pay": summary.tax_to_pay
            })
        
        return PIT38Summary(
            total_income=total_income,
            total_cost=total_cost,
            profit=profit,
            loss=loss,
            tax_base=tax_base,
            tax_due=tax_due,
            dividend_data=dividend_data
        )
    
    def _generate_pitzg_data(
        self, 
        fifo_result: FifoCalculationResult, 
        dividend_result: DividendCalculationResult
    ) -> List[PITZGData]:
        """Generate PIT/ZG data from calculation results"""
        fifo_df = fifo_result.to_dataframe()
        pitzg_data = []
        
        if not fifo_df.empty:
            # Group by country
            country_groups = fifo_df.groupby('country')
            
            for country, group in country_groups:
                # Calculate totals for this country
                securities_income = Decimal(str(group['income_pln'].sum()))
                securities_cost = Decimal(str(group['cost_pln'].sum()))
                securities_profit = max(Decimal('0'), securities_income - securities_cost)
                
                # Should be included in official PIT/ZG only if there's profit
                include_in_official_form = securities_profit > 0
                
                # Check if any row requires verification
                requires_verification = "(from ISIN)" in country
                
                pitzg_data.append(PITZGData(
                    country=country,
                    include_in_official_form=include_in_official_form,
                    requires_verification=requires_verification,
                    securities_income=securities_income,
                    securities_cost=securities_cost,
                    securities_profit=securities_profit,
                    tax_paid_abroad=Decimal('0')  # Usually 0 for securities
                ))
        
        return pitzg_data
