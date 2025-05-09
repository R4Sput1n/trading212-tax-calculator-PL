from abc import ABC, abstractmethod
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

from utils.date_utils import is_business_day, get_previous_business_day


class ExchangeRateService(ABC):
    """Abstract base class for exchange rate services"""
    
    @abstractmethod
    def get_exchange_rate(self, date: datetime, currency_code: str) -> Optional[float]:
        """
        Get exchange rate for specified date and currency.
        
        Args:
            date: Date for which to get the exchange rate
            currency_code: Currency code (e.g., 'USD', 'EUR')
            
        Returns:
            Exchange rate or None if not available
        """
        pass


class NBPExchangeRateService(ExchangeRateService):
    """Exchange rate service using NBP (National Bank of Poland) API"""
    
    def __init__(self, base_url: str = "http://api.nbp.pl/api/exchangerates/rates/a"):
        """
        Initialize NBPExchangeRateService.
        
        Args:
            base_url: Base URL for NBP API (default: http://api.nbp.pl/api/exchangerates/rates/a)
        """
        self.base_url = base_url
        self._cache: Dict[str, float] = {}  # Cache for exchange rates
    
    def get_exchange_rate(self, date: datetime, currency_code: str) -> Optional[float]:
        """
        Get exchange rate from NBP API for specified date and currency.
        For GBX (British pence), converts to GBP and divides by 100.
        Uses exchange rate from the last business day before the specified date.
        
        Args:
            date: Date for which to get the exchange rate
            currency_code: Currency code (e.g., 'USD', 'EUR', 'GBX')
            
        Returns:
            Exchange rate or None if not available
        """
        # Return 1.0 for PLN
        if currency_code == "PLN":
            return 1.0
        
        # Use cache if available
        cache_key = f"{date.strftime('%Y-%m-%d')}_{currency_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Save original currency code
        original_currency = currency_code
        factor = 1.0
        
        # Convert GBX (British pence) to GBP (British pound)
        if currency_code == "GBX":
            currency_code = "GBP"
            factor = 100.0  # 1 GBP = 100 GBX
        
        # Get previous business day
        prev_business_day = get_previous_business_day(date)
        formatted_date = prev_business_day.strftime("%Y-%m-%d")
        
        # Get data from NBP API
        url = f"{self.base_url}/{currency_code}/{formatted_date}/"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                rate = data["rates"][0]["mid"]
                
                # Adjust rate for original currency
                if original_currency == "GBX":
                    rate = rate / factor  # Divide by 100 to get rate for 1 GBX
                
                # Cache the result
                self._cache[cache_key] = rate
                
                return rate
            else:
                # Try again with the previous business day
                prev_business_day = get_previous_business_day(prev_business_day)
                formatted_date = prev_business_day.strftime("%Y-%m-%d")
                url = f"{self.base_url}/{currency_code}/{formatted_date}/"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    rate = data["rates"][0]["mid"]
                    
                    # Adjust rate for original currency
                    if original_currency == "GBX":
                        rate = rate / factor
                    
                    # Cache the result
                    self._cache[cache_key] = rate
                    
                    return rate
                else:
                    print(f"Could not get exchange rate for {original_currency} on {formatted_date}")
                    return None
        except Exception as e:
            print(f"Error getting exchange rate: {e}")
            return None


class MockExchangeRateService(ExchangeRateService):
    """Mock exchange rate service for testing"""
    
    def __init__(self, default_rate: float = 4.0):
        """
        Initialize MockExchangeRateService.
        
        Args:
            default_rate: Default exchange rate to return (default: 4.0)
        """
        self.default_rate = default_rate
        self.rates = {
            'USD': 4.0,
            'EUR': 4.5,
            'GBP': 5.0,
            'GBX': 0.05,  # 1/100 of GBP
            'PLN': 1.0
        }
    
    def get_exchange_rate(self, date: datetime, currency_code: str) -> Optional[float]:
        """
        Get mock exchange rate for specified currency.
        
        Args:
            date: Date for which to get the exchange rate (ignored)
            currency_code: Currency code (e.g., 'USD', 'EUR')
            
        Returns:
            Exchange rate or default rate if currency code not found
        """
        return self.rates.get(currency_code, self.default_rate)
