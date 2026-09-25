"""
PDF File Handler.
Supports extracting structured tables from .pdf documents using pdfplumber,
with sheet/page navigation, table merging, and DataFrame ingestion.
"""

import os
from typing import Dict, Any, Tuple, List
import pandas as pd
from handlers.base_handler import BaseHandler
from conversion.pdf_converter import (
    inspect_pdf_tables,
    extract_pdf_tables_to_df,
    HAS_PDFPLUMBER,
)


class PDFHandler(BaseHandler):
    EXTENSIONS = {".pdf"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def get_sheets(self, file_path: str) -> List[str]:
        """Returns list of tables/pages detected in the PDF."""
        if not HAS_PDFPLUMBER:
            return []
        try:
            info = inspect_pdf_tables(file_path)
            tables = info.get("tables", [])
            sheet_names = [t["name"] for t in tables]
            if len(sheet_names) > 1:
                sheet_names.insert(0, "All Tables (Combined)")
            return sheet_names
        except Exception:
            return []

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        sheet_name = kwargs.get("sheet_name")
        df, meta = extract_pdf_tables_to_df(file_path, table_selection=sheet_name)
        return df, meta
