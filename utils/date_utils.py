from datetime import datetime, timedelta
from typing import Optional


def is_business_day(date: datetime) -> bool:
    """
    Check if a date is a business day (not a weekend).
    
    Args:
        date: Date to check
        
    Returns:
        True if date is a business day, False otherwise
    """
    return date.weekday() < 5  # 0-4 are Monday to Friday


def get_previous_business_day(date: datetime) -> datetime:
    """
    Get the previous business day before the specified date.
    
    Args:
        date: Starting date
        
    Returns:
        Previous business day
    """
    date = date - timedelta(days=1)
    while not is_business_day(date):
        date = date - timedelta(days=1)
    return date


def get_next_business_day(date: datetime) -> datetime:
    """
    Get the next business day after the specified date.
    
    Args:
        date: Starting date
        
    Returns:
        Next business day
    """
    date = date + timedelta(days=1)
    while not is_business_day(date):
        date = date + timedelta(days=1)
    return date


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    Handles various date formats flexibly.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        from dateutil.parser import parse
        return parse(date_str)
    except Exception as e:
        print(f"Failed to parse date: {date_str}, error: {e}")
        return None


def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        date: Datetime object to format
        format_str: Format string (default: %Y-%m-%d)
        
    Returns:
        Formatted date string
    """
    return date.strftime(format_str)


def get_year_start(date: datetime) -> datetime:
    """
    Get the start of the year for the specified date.
    
    Args:
        date: Date to get year start for
        
    Returns:
        Start of year datetime
    """
    return datetime(date.year, 1, 1)


def get_year_end(date: datetime) -> datetime:
    """
    Get the end of the year for the specified date.
    
    Args:
        date: Date to get year end for
        
    Returns:
        End of year datetime
    """
    return datetime(date.year, 12, 31, 23, 59, 59, 999999)
