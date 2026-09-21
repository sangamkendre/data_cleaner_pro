"""
Excel File Handler.
Supports .xlsx, .xls, .xlsm, and .xlsb with high-performance Rust-based calamine engine,
falling back to openpyxl for maximum compatibility.
"""

import os
from typing import Dict, Any, Tuple, List
import pandas as pd
from handlers.base_handler import BaseHandler

try:
    import python_calamine
    HAS_CALAMINE = True
except ImportError:
    HAS_CALAMINE = False


class ExcelHandler(BaseHandler):
    EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def get_sheets(self, file_path: str) -> List[str]:
        """Returns list of sheets available in the Excel workbook."""
        if HAS_CALAMINE:
            try:
                wb = python_calamine.CalamineWorkbook.from_path(file_path)
                return list(wb.sheet_names)
            except Exception:
                pass
        try:
            with pd.ExcelFile(file_path) as excel_file:
                return list(excel_file.sheet_names)
        except Exception:
            return []

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        sheets = self.get_sheets(file_path)
        sheet_name = kwargs.get("sheet_name")

        if not sheet_name and sheets:
            sheet_name = sheets[0]

        df = None
        # Try high-performance calamine engine first (vastly faster and low memory)
        if HAS_CALAMINE:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine="calamine")
            except Exception:
                df = None

        if df is None:
            # Fallback to default engine (openpyxl for xlsx/xlsm)
            df = pd.read_excel(file_path, sheet_name=sheet_name)

        metadata = {
            "format": "Excel",
            "sheets": sheets,
            "selected_sheet": sheet_name,
            "rows": len(df),
            "columns": len(df.columns),
        }
        return df, metadata
