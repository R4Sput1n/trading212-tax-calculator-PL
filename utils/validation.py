from typing import List, Dict, Any, Callable, TypeVar, Generic, Optional
from decimal import Decimal

T = TypeVar('T')


class Validator(Generic[T]):
    """Generic validator for data objects"""
    
    def __init__(self):
        """Initialize validator with empty validation rules"""
        self.validations: List[Dict[str, Any]] = []
    
    def add_rule(self, field: str, rule: Callable[[T], bool], message: str):
        """
        Add a validation rule.
        
        Args:
            field: Field name to validate
            rule: Function that takes the object and returns True if valid, False otherwise
            message: Error message to return if validation fails
        """
        self.validations.append({
            'field': field,
            'rule': rule,
            'message': message
        })
        return self
    
    def validate(self, obj: T) -> List[str]:
        """
        Validate an object against all rules.
        
        Args:
            obj: Object to validate
            
        Returns:
            List of error messages for failed validations
        """
        errors = []
        
        for validation in self.validations:
            try:
                if not validation['rule'](obj):
                    errors.append(f"{validation['field']}: {validation['message']}")
            except Exception as e:
                errors.append(f"{validation['field']}: Validation error: {str(e)}")
        
        return errors


def is_positive_decimal(value: Optional[Decimal]) -> bool:
    """Check if a Decimal value is positive"""
    return value is not None and value > 0


def is_non_negative_decimal(value: Optional[Decimal]) -> bool:
    """Check if a Decimal value is non-negative"""
    return value is not None and value >= 0


def is_not_empty(value: str) -> bool:
    """Check if a string value is not empty"""
    return value is not None and value.strip() != ''


def is_valid_isin(isin: str) -> bool:
    """
    Check if an ISIN code is valid.
    ISIN codes are 12 characters, start with a two-letter country code,
    followed by 9 alphanumeric characters, and a check digit.
    
    Args:
        isin: ISIN code to validate
        
    Returns:
        True if ISIN is valid, False otherwise
    """
    if not isin or not isinstance(isin, str):
        return False
    
    # Basic format check
    isin = isin.strip().upper()
    if len(isin) != 12:
        return False
    
    # Check if first two characters are letters (country code)
    if not isin[:2].isalpha():
        return False
    
    # Check if rest of the characters are alphanumeric
    if not isin[2:].isalnum():
        return False
    
    # More sophisticated validation can be added here, such as check digit validation
    
    return True
