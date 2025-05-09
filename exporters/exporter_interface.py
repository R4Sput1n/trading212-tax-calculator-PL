from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic

# Define generic types
T = TypeVar('T')  # Input type


class ExporterInterface(Generic[T], ABC):
    """Abstract base class for exporters"""
    
    @abstractmethod
    def export(self, data: T, output_path: str) -> bool:
        """
        Export data to a file.
        
        Args:
            data: Data to export
            output_path: Path to the output file
            
        Returns:
            True if export was successful, False otherwise
        """
        pass
