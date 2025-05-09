from abc import ABC, abstractmethod
from typing import List, Dict, Any, TypeVar, Generic

from models.transaction import Transaction

# Define generic types
T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type


class CalculatorInterface(Generic[T, R], ABC):
    """Abstract base class for tax calculators"""
    
    @abstractmethod
    def calculate(self, data: T) -> R:
        """
        Calculate tax data based on input data.
        
        Args:
            data: Input data for calculation
            
        Returns:
            Calculation result
        """
        pass
    
    @abstractmethod
    def validate(self, data: T) -> List[str]:
        """
        Validate input data before calculation.
        
        Args:
            data: Input data to validate
            
        Returns:
            List of validation issues, empty if no issues
        """
        pass
