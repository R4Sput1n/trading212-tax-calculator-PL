"""
Application settings and constants
"""
from decimal import Decimal
import os
from pathlib import Path


class Settings:
    """Application settings"""
    
    # Application name and version
    APP_NAME = "Trading212 Tax Calculator"
    APP_VERSION = "1.0.0"
    
    # Default directories
    DEFAULT_DATA_DIR = "data"
    DEFAULT_OUTPUT_DIR = "output"
    
    # Default file paths
    DEFAULT_PROCESSED_FILE = os.path.join(DEFAULT_DATA_DIR, "processed_data.csv")
    DEFAULT_REPORT_FILE = os.path.join(DEFAULT_OUTPUT_DIR, "tax_report.xlsx")
    DEFAULT_LOG_FILE = os.path.join(DEFAULT_OUTPUT_DIR, "tax_calculator.log")
    
    # Tax calculation
    DEFAULT_TAX_RATE = Decimal('0.19')  # 19% tax rate in Poland
    
    # API settings
    NBP_API_BASE_URL = "http://api.nbp.pl/api/exchangerates/rates/a"
    
    # Create directories if they don't exist
    @classmethod
    def init_directories(cls):
        """Create default directories if they don't exist"""
        for directory in [cls.DEFAULT_DATA_DIR, cls.DEFAULT_OUTPUT_DIR]:
            Path(directory).mkdir(exist_ok=True)


# Create a single instance to be imported elsewhere
settings = Settings()
