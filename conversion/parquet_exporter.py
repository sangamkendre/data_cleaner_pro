"""
Parquet Exporter Engine.
Exports DataFrame to optimized Apache Parquet format.
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
from profiling.file_info import format_size


def export_to_parquet(
    df: pd.DataFrame,
    output_path: str,
    compression: str = "snappy",
) -> Tuple[str, Dict[str, Any]]:
    """
    Exports a DataFrame to a Parquet file.
    Ensures column data types are safe for Parquet serialization.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df_export = df.copy()

    # Parquet requires string column names
    df_export.columns = [str(c) for c in df_export.columns]

    # Handle object columns: replace mixed object types with clean string or nulls
    for col in df_export.select_dtypes(include=["object", "string", "str"]).columns:
        mask = df_export[col].notna()
        df_export.loc[mask, col] = df_export.loc[mask, col].astype(str)

    try:
        df_export.to_parquet(output_path, engine="pyarrow", compression=compression, index=False)
    except ImportError:
        try:
            df_export.to_parquet(output_path, engine="fastparquet", compression=compression, index=False)
        except ImportError:
            raise ImportError(
                "Exporting to Parquet requires 'pyarrow' or 'fastparquet'. "
                "Please install pyarrow via: pip install pyarrow"
            )
    except Exception as pyarrow_err:
        # Fallback with fastparquet
        try:
            df_export.to_parquet(output_path, engine="fastparquet", compression=compression, index=False)
        except Exception:
            raise pyarrow_err

    file_size_bytes = os.path.getsize(output_path)

    metadata = {
        "format": "Parquet",
        "file_path": output_path,
        "file_name": os.path.basename(output_path),
        "file_size": format_size(file_size_bytes),
        "file_size_bytes": file_size_bytes,
        "rows": len(df_export),
        "columns": len(df_export.columns),
        "compression": compression,
    }
    return output_path, metadata
