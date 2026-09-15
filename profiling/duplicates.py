"""
Duplicate Detection Profiler.
Finds duplicate rows and provides sample duplicate records for user inspection.
"""

from typing import Dict, Any, List
import pandas as pd


def analyze_duplicates(df: pd.DataFrame, subset: List[str] = None) -> Dict[str, Any]:
    total_rows = len(df)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "duplicate_rows": 0,
            "duplicate_percentage": 0.0,
            "sample_duplicates": [],
            "has_duplicates": False,
        }

    dup_mask = df.duplicated(subset=subset, keep=False)
    dup_count = int(df.duplicated(subset=subset, keep="first").sum())
    dup_percentage = round((dup_count / total_rows) * 100, 2)

    # Get sample duplicate rows (first 50 duplicate records)
    sample_df = df[dup_mask].head(50)
    sample_records = []
    for idx, row in sample_df.iterrows():
        record = row.to_dict()
        record["_row_index"] = int(idx)
        sample_records.append(record)

    return {
        "total_rows": total_rows,
        "duplicate_rows": dup_count,
        "duplicate_percentage": dup_percentage,
        "sample_duplicates": sample_records,
        "has_duplicates": dup_count > 0,
    }
