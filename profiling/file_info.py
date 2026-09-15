"""
File Information Profiler.
Calculates size, row count, column count, and memory usage.
"""

import os
from typing import Dict, Any
import pandas as pd


def format_size(bytes_size: int) -> str:
    """Formats bytes into human readable KB, MB, GB."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def get_file_info(df: pd.DataFrame, file_path: str = None, filename: str = None, file_type: str = "Unknown") -> Dict[str, Any]:
    """Generates file overview metrics."""
    file_size_bytes = 0
    if file_path and os.path.exists(file_path):
        file_size_bytes = os.path.getsize(file_path)
    else:
        # Approximate memory usage of dataframe
        file_size_bytes = int(df.memory_usage(deep=True).sum())

    return {
        "file_name": filename or (os.path.basename(file_path) if file_path else "dataset"),
        "file_type": file_type,
        "file_size": format_size(file_size_bytes),
        "file_size_bytes": file_size_bytes,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "memory_usage": format_size(int(df.memory_usage(deep=True).sum())),
        "column_names": list(df.columns),
    }
