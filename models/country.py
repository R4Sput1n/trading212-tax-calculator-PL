from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Country:
    """Country information model"""
    code: str  # ISO 3166-1 alpha-2 code (e.g., "US", "GB")
    name: str  # Full country name (e.g., "United States", "United Kingdom")
    name_pl: str  # Country name in Polish (for tax forms)
    isin_prefix: str  # ISIN country prefix (usually the same as code)
    tax_treaty: bool = False  # Whether Poland has a tax treaty with this country
    withholding_tax_rate: Optional[float] = None  # Standard withholding tax rate
    
    @property
    def display_name(self) -> str:
        """Get display name including code and Polish name"""
        return f"{self.name} ({self.code}) / {self.name_pl}"


class CountryRegistry:
    """Registry of countries with support information"""
    
    def __init__(self):
        """Initialize country registry with common countries"""
        self.countries: Dict[str, Country] = {}
        self._init_common_countries()
    
    def _init_common_countries(self):
        """Initialize registry with common countries used in stock trading"""
        countries = [
            Country("US", "United States", "Stany Zjednoczone", "US", True, 15.0),
            Country("GB", "United Kingdom", "Wielka Brytania", "GB", True, 10.0),
            Country("DE", "Germany", "Niemcy", "DE", True, 15.0),
            Country("FR", "France", "Francja", "FR", True, 15.0),
            Country("CH", "Switzerland", "Szwajcaria", "CH", True, 15.0),
            Country("IE", "Ireland", "Irlandia", "IE", True, 15.0),
            Country("NL", "Netherlands", "Holandia", "NL", True, 15.0),
            Country("SE", "Sweden", "Szwecja", "SE", True, 15.0),
            Country("ES", "Spain", "Hiszpania", "ES", True, 15.0),
            Country("IT", "Italy", "Włochy", "IT", True, 15.0),
            Country("JP", "Japan", "Japonia", "JP", True, 10.0),
            Country("CA", "Canada", "Kanada", "CA", True, 15.0),
            Country("AU", "Australia", "Australia", "AU", True, 15.0),
            Country("DK", "Denmark", "Dania", "DK", True, 15.0),
            Country("FI", "Finland", "Finlandia", "FI", True, 15.0),
            Country("NO", "Norway", "Norwegia", "NO", True, 15.0),
            Country("BE", "Belgium", "Belgia", "BE", True, 15.0),
            Country("LU", "Luxembourg", "Luksemburg", "LU", True, 15.0),
            Country("HK", "Hong Kong", "Hongkong", "HK", False, 0.0),
            Country("SG", "Singapore", "Singapur", "SG", True, 10.0),
            Country("KR", "South Korea", "Korea Południowa", "KR", True, 10.0),
            Country("CN", "China", "Chiny", "CN", True, 10.0),
            Country("IN", "India", "Indie", "IN", True, 10.0),
            Country("RU", "Russia", "Rosja", "RU", True, 10.0),
            Country("BR", "Brazil", "Brazylia", "BR", True, 15.0),
            Country("ZA", "South Africa", "Republika Południowej Afryki", "ZA", True, 10.0),
            Country("PL", "Poland", "Polska", "PL", False, 19.0),
        ]
        
        for country in countries:
            self.add_country(country)
    
    def add_country(self, country: Country):
        """Add a country to the registry"""
        self.countries[country.code] = country
        # Also index by name and ISIN prefix if they differ from code
        if country.name != country.code:
            self.countries[country.name] = country
        if country.isin_prefix != country.code:
            self.countries[country.isin_prefix] = country
    
    def get_country(self, identifier: str) -> Optional[Country]:
        """
        Get a country by code, name, or ISIN prefix.
        
        Args:
            identifier: Country code, name, or ISIN prefix
            
        Returns:
            Country object if found, None otherwise
        """
        return self.countries.get(identifier)
    
    def get_all_countries(self) -> Dict[str, Country]:
        """Get all registered countries"""
        return self.countries.copy()


# Create a singleton instance
country_registry = CountryRegistry()
