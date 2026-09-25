"""
File Handlers Package.
Provides registry and auto-detection of format-specific handlers.
"""

from typing import List, Optional
from handlers.base_handler import BaseHandler
from handlers.csv_handler import CSVHandler
from handlers.excel_handler import ExcelHandler
from handlers.parquet_handler import ParquetHandler
from handlers.sql_handler import SQLHandler
from handlers.pdf_handler import PDFHandler

HANDLERS: List[BaseHandler] = [
    CSVHandler(),
    ExcelHandler(),
    ParquetHandler(),
    SQLHandler(),
    PDFHandler(),
]


def get_handler_for_file(filename: str) -> Optional[BaseHandler]:
    """Finds the appropriate file handler for the given filename."""
    for handler in HANDLERS:
        if handler.can_handle(filename):
            return handler
    return None


__all__ = [
    "BaseHandler",
    "CSVHandler",
    "ExcelHandler",
    "ParquetHandler",
    "SQLHandler",
    "PDFHandler",
    "get_handler_for_file",
    "HANDLERS",
]
