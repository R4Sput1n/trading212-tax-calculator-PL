from abc import ABC, abstractmethod
from typing import Optional, Dict


class ISINService(ABC):
    """Abstract base class for ISIN code services"""
    
    @abstractmethod
    def get_country_from_isin(self, isin: str) -> Optional[str]:
        """
        Get country name from ISIN prefix.
        
        Args:
            isin: ISIN code
            
        Returns:
            Country name or None if not available
        """
        pass


class DefaultISINService(ISINService):
    """Default implementation of ISIN service"""
    
    def __init__(self):
        """Initialize DefaultISINService with ISIN country codes"""
        # Map of ISIN country codes to country names
        self.isin_country_codes = {
            'AT': 'Austria',
            'AU': 'Australia',
            'BE': 'Belgium',
            'BM': 'Bermuda',
            'CA': 'Canada',
            'CH': 'Switzerland',
            'CN': 'China',
            'DE': 'Germany',
            'DK': 'Denmark',
            'ES': 'Spain',
            'FI': 'Finland',
            'FR': 'France',
            'GB': 'United Kingdom',
            'GR': 'Greece',
            'HK': 'Hong Kong',
            'IE': 'Ireland',
            'IL': 'Israel',
            'IN': 'India',
            'IT': 'Italy',
            'JP': 'Japan',
            'KR': 'South Korea',
            'LU': 'Luxembourg',
            'MX': 'Mexico',
            'NL': 'Netherlands',
            'NO': 'Norway',
            'NZ': 'New Zealand',
            'PT': 'Portugal',
            'RU': 'Russia',
            'SE': 'Sweden',
            'SG': 'Singapore',
            'US': 'United States',
            'ZA': 'South Africa'
        }
    
    def get_country_from_isin(self, isin: str) -> Optional[str]:
        """
        Get country name from ISIN prefix (first two letters).
        
        Args:
            isin: ISIN code
            
        Returns:
            Country name or None if ISIN is invalid or country not recognized
        """
        if not isin or len(isin) < 2:
            return None
        
        prefix = isin[:2].upper()
        return self.isin_country_codes.get(prefix)


class MockISINService(ISINService):
    """Mock ISIN service for testing"""
    
    def __init__(self):
        """Initialize MockISINService with a few country codes"""
        self.country_codes = {
            'US': 'United States',
            'GB': 'United Kingdom',
            'DE': 'Germany',
            'FR': 'France',
            'CH': 'Switzerland',
            'JP': 'Japan'
        }
    
    def get_country_from_isin(self, isin: str) -> Optional[str]:
        """
        Get mock country from ISIN prefix.
        
        Args:
            isin: ISIN code
            
        Returns:
            Country name or None if ISIN is invalid or prefix not found
        """
        if not isin or len(isin) < 2:
            return None
        
        prefix = isin[:2].upper()
        return self.country_codes.get(prefix)
