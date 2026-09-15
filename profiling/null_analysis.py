"""
Null Value Analysis Profiler.
Analyzes missing values per column and across the entire dataset.
"""

from typing import Dict, Any, List
import pandas as pd


def analyze_nulls(df: pd.DataFrame) -> Dict[str, Any]:
    total_rows = len(df)
    total_cells = total_rows * len(df.columns) if total_rows > 0 else 1

    columns_analysis = []
    columns_with_nulls_count = 0
    total_empty_strings = 0
    total_missing_cells = 0

    for col in df.columns:
        series = df[col]
        na_count = int(series.isna().sum())

        # Check for empty and whitespace-only strings
        empty_str_count = 0
        if series.dtype == "object" or str(series.dtype) == "string" or pd.api.types.is_string_dtype(series):
            not_na = series.dropna()
            if not not_na.empty:
                empty_str_count = int((not_na.astype(str).str.strip() == "").sum())

        total_empty_strings += empty_str_count
        null_count = na_count + empty_str_count
        total_missing_cells += null_count
        null_pct = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        non_null_count = total_rows - null_count
        dup_val_count = max(0, non_null_count - unique_count)

        if null_count > 0:
            columns_with_nulls_count += 1

        columns_analysis.append({
            "column": col,
            "data_type": str(series.dtype),
            "total_values": total_rows,
            "null_count": null_count,
            "na_count": na_count,
            "empty_string_count": empty_str_count,
            "null_percentage": null_pct,
            "unique_values": unique_count,
            "duplicate_values": dup_val_count,
            "status": "⚠" if null_count > 0 else "✓",
            "action": "Fix" if null_count > 0 else "—",
        })

    overall_null_pct = round((total_missing_cells / total_cells) * 100, 2) if total_cells > 0 else 0.0

    return {
        "total_nulls": total_missing_cells,
        "overall_null_percentage": overall_null_pct,
        "columns_with_nulls": columns_with_nulls_count,
        "total_empty_strings": total_empty_strings,
        "columns": columns_analysis,
    }

