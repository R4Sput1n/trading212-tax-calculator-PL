from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from models.transaction import Transaction


class ParserInterface(ABC):
    """Abstract base class for transaction data parsers"""
    
    @abstractmethod
    def parse_file(self, file_path: str) -> List[Transaction]:
        """
        Parse a file and return a list of Transaction objects.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            List of Transaction objects
        """
        pass
    
    @abstractmethod
    def parse_files(self, file_paths: List[str]) -> List[Transaction]:
        """
        Parse multiple files and return a combined list of Transaction objects.
        
        Args:
            file_paths: List of paths to the files to parse
            
        Returns:
            Combined list of Transaction objects
        """
        pass
    
    @abstractmethod
    def parse_data(self, data: Any) -> List[Transaction]:
        """
        Parse data in memory and return a list of Transaction objects.
        
        Args:
            data: Data to parse (format depends on parser implementation)
            
        Returns:
            List of Transaction objects
        """
        pass
