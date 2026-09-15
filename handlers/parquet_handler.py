"""
Parquet File Handler.
Supports Apache Parquet columnar storage format.
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
from handlers.base_handler import BaseHandler


class ParquetHandler(BaseHandler):
    EXTENSIONS = {".parquet", ".pq"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        try:
            df = pd.read_parquet(file_path)
        except Exception:
            df = pd.read_parquet(file_path, engine="fastparquet")

        metadata = {
            "format": "Parquet",
            "rows": len(df),
            "columns": len(df.columns),
        }
        return df, metadata
