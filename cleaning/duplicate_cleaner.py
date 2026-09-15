"""
Duplicate Cleaning Engine.
Deduplicates datasets based on entire row or subset of key columns.
"""

from typing import Tuple, List, Optional
import pandas as pd


def remove_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: str = "first",  # 'first', 'last'
) -> Tuple[pd.DataFrame, int]:
    """
    Removes duplicate rows.
    Returns:
        (updated_df, rows_removed_count)
    """
    initial_rows = len(df)
    clean_keep = keep if keep in ("first", "last") else "first"
    clean_subset = [c for c in subset if c in df.columns] if subset else None

    df_cleaned = df.drop_duplicates(subset=clean_subset, keep=clean_keep)
    rows_removed = initial_rows - len(df_cleaned)

    return df_cleaned, rows_removed
