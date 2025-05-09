from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import yfinance as yf

from services.isin_service import ISINService


class CompanyInfoService(ABC):
    """Abstract base class for company information services"""
    
    @abstractmethod
    def get_company_country(self, isin: str, name: str) -> str:
        """
        Get country of registration for a company.
        
        Args:
            isin: ISIN code of the company
            name: Name of the company
            
        Returns:
            Country name or "Unknown" if not available
        """
        pass


class YFinanceCompanyInfoService(CompanyInfoService):
    """Company information service using yfinance library"""
    
    def __init__(self, isin_service: ISINService):
        """
        Initialize YFinanceCompanyInfoService.
        
        Args:
            isin_service: Service for ISIN code lookups
        """
        self.isin_service = isin_service
        self._cache: Dict[str, str] = {}  # Cache for company countries
    
    def get_company_country(self, isin: str, name: str) -> str:
        """
        Get country of registration for a company using yfinance.
        Falls back to ISIN country lookup if yfinance fails.
        
        Args:
            isin: ISIN code of the company
            name: Name of the company
            
        Returns:
            Country name or "Unknown" if not available
        """
        # Use cache if available
        if isin in self._cache:
            return self._cache[isin]
        
        try:
            # Use ISIN as ticker
            stock = yf.Ticker(isin)
            info = stock.info
            
            if "country" in info and info["country"]:
                # Cache the result
                self._cache[isin] = info["country"]
                return info["country"]
            else:
                # Fall back to ISIN country lookup
                isin_country = self.isin_service.get_country_from_isin(isin)
                
                if isin_country:
                    # Mark as requiring verification
                    country = f"{isin_country} (from ISIN)"
                    
                    # Cache the result
                    self._cache[isin] = country
                    
                    return country
                else:
                    # Cache the result
                    self._cache[isin] = "Unknown"
                    
                    return "Unknown"
        except Exception as e:
            print(f"Could not determine country for {isin} ({name}): {e}")
            
            # Fall back to ISIN country lookup
            isin_country = self.isin_service.get_country_from_isin(isin)
            
            if isin_country:
                # Mark as requiring verification
                country = f"{isin_country} (from ISIN)"
                
                # Cache the result
                self._cache[isin] = country
                
                return country
            else:
                # Cache the result
                self._cache[isin] = "Unknown"
                
                return "Unknown"


class MockCompanyInfoService(CompanyInfoService):
    """Mock company information service for testing"""
    
    def __init__(self, isin_service: ISINService = None):
        """
        Initialize MockCompanyInfoService.
        
        Args:
            isin_service: Service for ISIN code lookups (optional)
        """
        self.isin_service = isin_service
        self.countries = {
            'US0378331005': 'United States',  # Apple
            'US0231351067': 'United States',  # Amazon
            'US5949181045': 'United States',  # Microsoft
            'US88160R1014': 'United States',  # Tesla
            'GB0031348658': 'United Kingdom',  # Barclays
            'GB00B1YW4409': 'United Kingdom',  # 3i Group
            'DE0007664039': 'Germany',  # Volkswagen
            'DE0007100000': 'Germany',  # Mercedes-Benz
            'FR0000131104': 'France',  # BNP Paribas
            'FR0000120271': 'France'   # Total
        }
    
    def get_company_country(self, isin: str, name: str) -> str:
        """
        Get mock country for a company.
        
        Args:
            isin: ISIN code of the company
            name: Name of the company
            
        Returns:
            Country name or result from ISIN service if available, otherwise "Unknown"
        """
        # Check if we have a predefined country
        if isin in self.countries:
            return self.countries[isin]
        
        # Fall back to ISIN country lookup if available
        if self.isin_service:
            isin_country = self.isin_service.get_country_from_isin(isin)
            if isin_country:
                return f"{isin_country} (from ISIN)"
        
        return "Unknown"
