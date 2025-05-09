from typing import Dict, Any, Optional

from config.settings import settings
from services.exchange_rate_service import ExchangeRateService, NBPExchangeRateService, MockExchangeRateService
from services.company_info_service import CompanyInfoService, YFinanceCompanyInfoService, MockCompanyInfoService
from services.isin_service import ISINService, DefaultISINService, MockISINService


class ServiceFactory:
    """Factory for creating service instances"""
    
    @staticmethod
    def create_exchange_rate_service(service_type: str = "nbp", **kwargs) -> ExchangeRateService:
        """
        Create an exchange rate service.
        
        Args:
            service_type: Type of service to create ("nbp" or "mock")
            **kwargs: Additional arguments for the service constructor
            
        Returns:
            ExchangeRateService instance
        """
        if service_type == "nbp":
            base_url = kwargs.get("base_url", settings.NBP_API_BASE_URL)
            return NBPExchangeRateService(base_url=base_url)
        elif service_type == "mock":
            default_rate = kwargs.get("default_rate", 4.0)
            return MockExchangeRateService(default_rate=default_rate)
        else:
            raise ValueError(f"Unknown exchange rate service type: {service_type}")
    
    @staticmethod
    def create_isin_service(service_type: str = "default", **kwargs) -> ISINService:
        """
        Create an ISIN service.
        
        Args:
            service_type: Type of service to create ("default" or "mock")
            **kwargs: Additional arguments for the service constructor
            
        Returns:
            ISINService instance
        """
        if service_type == "default":
            return DefaultISINService()
        elif service_type == "mock":
            return MockISINService()
        else:
            raise ValueError(f"Unknown ISIN service type: {service_type}")
    
    @staticmethod
    def create_company_info_service(
        service_type: str = "yfinance", 
        isin_service: Optional[ISINService] = None,
        **kwargs
    ) -> CompanyInfoService:
        """
        Create a company info service.
        
        Args:
            service_type: Type of service to create ("yfinance" or "mock")
            isin_service: ISIN service to use (if None, a new one will be created)
            **kwargs: Additional arguments for the service constructor
            
        Returns:
            CompanyInfoService instance
        """
        # Create ISIN service if not provided
        if isin_service is None:
            isin_service_type = kwargs.get("isin_service_type", "default")
            isin_service = ServiceFactory.create_isin_service(isin_service_type)
        
        if service_type == "yfinance":
            return YFinanceCompanyInfoService(isin_service=isin_service)
        elif service_type == "mock":
            return MockCompanyInfoService(isin_service=isin_service)
        else:
            raise ValueError(f"Unknown company info service type: {service_type}")
    
    @staticmethod
    def create_all_services(use_mock: bool = False) -> Dict[str, Any]:
        """
        Create all services.
        
        Args:
            use_mock: Whether to use mock services (for testing)
            
        Returns:
            Dictionary of service instances
        """
        # Determine service types
        exchange_rate_service_type = "mock" if use_mock else "nbp"
        isin_service_type = "mock" if use_mock else "default"
        company_info_service_type = "mock" if use_mock else "yfinance"
        
        # Create services
        isin_service = ServiceFactory.create_isin_service(isin_service_type)
        exchange_rate_service = ServiceFactory.create_exchange_rate_service(exchange_rate_service_type)
        company_info_service = ServiceFactory.create_company_info_service(
            company_info_service_type, 
            isin_service=isin_service
        )
        
        return {
            'isin_service': isin_service,
            'exchange_rate_service': exchange_rate_service,
            'company_info_service': company_info_service
        }
