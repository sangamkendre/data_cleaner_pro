"""
Excel File Handler.
Supports .xlsx and .xls with automatic sheet detection and sheet selection.
"""

import os
from typing import Dict, Any, Tuple, List
import pandas as pd
from handlers.base_handler import BaseHandler


class ExcelHandler(BaseHandler):
    EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def get_sheets(self, file_path: str) -> List[str]:
        """Returns list of sheets available in the Excel workbook."""
        try:
            with pd.ExcelFile(file_path) as excel_file:
                return excel_file.sheet_names
        except Exception:
            return []

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        sheets = self.get_sheets(file_path)
        sheet_name = kwargs.get("sheet_name")

        if not sheet_name and sheets:
            sheet_name = sheets[0]

        df = pd.read_excel(file_path, sheet_name=sheet_name)

        metadata = {
            "format": "Excel",
            "sheets": sheets,
            "selected_sheet": sheet_name,
            "rows": len(df),
            "columns": len(df.columns),
        }
        return df, metadata
