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
            # Prefer pyarrow for broadest feature and compression support
            df = pd.read_parquet(file_path, engine="pyarrow")
        except ImportError:
            # Fallback to fastparquet if pyarrow is not installed
            try:
                df = pd.read_parquet(file_path, engine="fastparquet")
            except ImportError:
                raise ImportError(
                    "Reading Parquet files requires 'pyarrow' or 'fastparquet'. "
                    "Please install pyarrow via: pip install pyarrow"
                )
        except Exception as pyarrow_err:
            # Try fastparquet as secondary fallback in case of engine incompatibility
            try:
                df = pd.read_parquet(file_path, engine="fastparquet")
            except Exception:
                # Re-raise the primary pyarrow error if both fail
                raise pyarrow_err

        metadata = {
            "format": "Parquet",
            "rows": len(df),
            "columns": len(df.columns),
        }
        return df, metadata
