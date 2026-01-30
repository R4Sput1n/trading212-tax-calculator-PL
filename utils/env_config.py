import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_personal_data(env_file: Optional[str] = '.env') -> Dict[str, str]:
    """
    Load personal data from environment variables or .env file.

    Args:
        env_file: Path to .env file (default: .env in current directory)

    Returns:
        Dictionary with personal data
    """
    # Try to load from .env file first
    if env_file and os.path.isfile(env_file):
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")

    # Define required personal fields
    personal_fields = [
        'FULLNAME',
        'PESEL',
        'ADDRESS',
        'CITY',
        'POSTAL_CODE',
        'TAX_OFFICE'
    ]

    # Load personal data from environment variables
    personal_data = {}
    for field in personal_fields:
        value = os.environ.get(field)
        if value:
            personal_data[field] = value
        else:
            logger.warning(f"Personal data field '{field}' not found in environment variables")
            personal_data[field] = f"UZUPEŁNIJ {field}"

    return personal_data
