from typing import Dict, Any, List, Tuple, Union
import pandas as pd

from exporters.exporter_interface import ExporterInterface


class ExcelExporter(ExporterInterface[Dict[str, pd.DataFrame]]):
    """Exporter for pandas DataFrames to Excel"""
    
    def export(self, data: Dict[str, pd.DataFrame], output_path: str) -> bool:
        """
        Export DataFrames to an Excel file with each DataFrame in a separate sheet.
        
        Args:
            data: Dictionary mapping sheet names to DataFrames
            output_path: Path to the output Excel file
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for sheet_name, df in data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"Data exported successfully to {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return False


class DetailedExcelExporter(ExporterInterface[Dict[str, Union[pd.DataFrame, List[Dict[str, Any]]]]]):
    """Advanced exporter for pandas DataFrames to Excel with more options"""
    
    def export(self, data: Dict[str, Union[pd.DataFrame, List[Dict[str, Any]]]], output_path: str) -> bool:
        """
        Export DataFrames or lists of dictionaries to an Excel file with each in a separate sheet.
        Allows for exporting both DataFrames and raw data.
        
        Args:
            data: Dictionary mapping sheet names to DataFrames or lists of dictionaries
            output_path: Path to the output Excel file
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for sheet_name, content in data.items():
                    if isinstance(content, pd.DataFrame):
                        # If content is a DataFrame, export directly
                        content.to_excel(writer, sheet_name=sheet_name, index=False)
                    elif isinstance(content, list) and content and isinstance(content[0], dict):
                        # If content is a list of dictionaries, convert to DataFrame first
                        df = pd.DataFrame(content)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        print(f"Warning: Skipping sheet '{sheet_name}' due to unsupported content type")
            
            print(f"Data exported successfully to {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return False
