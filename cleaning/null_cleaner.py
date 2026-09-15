"""
Null Value Cleaning Engine.
Provides strategies to impute, replace, or drop missing values.
"""

from typing import Tuple, Optional, Any
import pandas as pd
import numpy as np


def clean_null_values(
    df: pd.DataFrame,
    column: Optional[str] = None,  # None means apply across all columns
    strategy: str = "replace",      # 'replace', 'remove_rows', 'mean', 'median', 'mode', 'ffill', 'bfill'
    fill_value: Any = "Unknown",
    treat_empty_as_null: bool = True,
) -> Tuple[pd.DataFrame, int, int]:
    """
    Handles null values.
    Returns:
        (updated_df, nulls_handled_count, rows_removed_count)
    """
    df = df.copy()
    initial_rows = len(df)
    target_cols = [column] if column and column in df.columns else list(df.columns)

    if treat_empty_as_null:
        for col in target_cols:
            series = df[col]
            if series.dtype == "object" or str(series.dtype) == "string" or pd.api.types.is_string_dtype(series):
                not_na = series.notna()
                if not_na.any():
                    empty_mask = series[not_na].astype(str).str.strip() == ""
                    empty_indices = series[not_na][empty_mask].index
                    if len(empty_indices) > 0:
                        df.loc[empty_indices, col] = np.nan

    initial_nulls = int(df[target_cols].isna().sum().sum())

    if strategy == "remove_rows":
        if column and column in df.columns:
            df = df.dropna(subset=[column])
        else:
            df = df.dropna(how="any")
        rows_removed = initial_rows - len(df)
        nulls_handled = initial_nulls - int(df[target_cols].isna().sum().sum())
        return df, nulls_handled, rows_removed

    for col in target_cols:
        col_null_mask = df[col].isna()
        if not col_null_mask.any():
            continue

        if strategy == "replace":
            df[col] = df[col].fillna(fill_value)
        elif strategy == "mean":
            numeric_series = pd.to_numeric(df[col], errors="coerce")
            mean_val = numeric_series.mean()
            if pd.notna(mean_val):
                df[col] = df[col].fillna(round(mean_val, 2))
            else:
                df[col] = df[col].fillna(fill_value)
        elif strategy == "median":
            numeric_series = pd.to_numeric(df[col], errors="coerce")
            med_val = numeric_series.median()
            if pd.notna(med_val):
                df[col] = df[col].fillna(round(med_val, 2))
            else:
                df[col] = df[col].fillna(fill_value)
        elif strategy == "mode":
            mode_vals = df[col].mode(dropna=True)
            if not mode_vals.empty:
                df[col] = df[col].fillna(mode_vals.iloc[0])
            else:
                df[col] = df[col].fillna(fill_value)
        elif strategy == "ffill":
            df[col] = df[col].ffill()
        elif strategy == "bfill":
            df[col] = df[col].bfill()

    final_nulls = int(df[target_cols].isna().sum().sum())
    nulls_handled = initial_nulls - final_nulls

    return df, nulls_handled, 0
