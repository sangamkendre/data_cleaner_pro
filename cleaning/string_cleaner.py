"""
String Cleaning Engine.
Provides whitespace trimming, extra spaces removal, case transformation,
and special character sanitization.
"""

import re
from typing import Tuple, List, Optional, Set
import numpy as np
import pandas as pd


def replace_empty_with_null(
    df: pd.DataFrame,
    column: Optional[str] = None,
    include_whitespace: bool = True,
    include_placeholders: bool = True,
    custom_placeholders: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, int]:
    """
    Detects empty strings ("") and whitespace-only strings ("   "),
    as well as common missing value placeholders, and replaces them with NaN.
    Returns (updated_df, count_of_replaced_cells).
    """
    df = df.copy()
    target_cols = [column] if column and column in df.columns else list(df.columns)
    total_replaced = 0

    placeholders: Set[str] = set()
    if include_placeholders:
        placeholders.update([
            "n/a", "na", "null", "none", "nan", "-", "--", "---", "?", "nil",
            "missing", "unknown", "undefined", "#n/a", "#na", "empty"
        ])
    if custom_placeholders:
        placeholders.update([p.lower().strip() for p in custom_placeholders if p])

    for col in target_cols:
        series = df[col]
        # Only process object / string columns (or mixed string columns)
        if series.dtype == "object" or str(series.dtype) == "string" or pd.api.types.is_string_dtype(series):
            not_na_mask = series.notna()
            if not not_na_mask.any():
                continue

            str_vals = series[not_na_mask].astype(str)
            if include_whitespace:
                trimmed = str_vals.str.strip()
                empty_mask = trimmed == ""
            else:
                trimmed = str_vals
                empty_mask = str_vals == ""

            if placeholders:
                ph_mask = trimmed.str.lower().isin(placeholders)
                match_mask = empty_mask | ph_mask
            else:
                match_mask = empty_mask

            indices_to_replace = str_vals[match_mask].index
            count = len(indices_to_replace)
            if count > 0:
                df.loc[indices_to_replace, col] = np.nan
                total_replaced += count

    return df, total_replaced


def clean_string_column(
    df: pd.DataFrame,
    column: str,
    trim_whitespace: bool = True,
    remove_extra_spaces: bool = True,
    case_transform: Optional[str] = None,  # 'lower', 'upper', 'title', 'capitalize', None
    remove_special_chars: bool = False,
    custom_regex_replace: Optional[Tuple[str, str]] = None,
    empty_to_null: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """
    Cleans a text column and returns (updated_df, modifications_count).
    """
    if column not in df.columns:
        return df, 0

    df = df.copy()
    original_series = df[column].copy()

    # Convert non-null to string
    mask = df[column].notna()
    series = df.loc[mask, column].astype(str)

    if trim_whitespace:
        series = series.str.strip()

    if remove_extra_spaces:
        series = series.str.replace(r"\s+", " ", regex=True)

    if case_transform == "lower":
        series = series.str.lower()
    elif case_transform == "upper":
        series = series.str.upper()
    elif case_transform == "title":
        series = series.str.title()
    elif case_transform == "capitalize":
        series = series.str.capitalize()

    if remove_special_chars:
        # Keep alphanumeric, spaces and standard punctuation like dashes
        series = series.str.replace(r"[^a-zA-Z0-9\s\-_\.]", "", regex=True)

    if custom_regex_replace and len(custom_regex_replace) == 2:
        pat, repl = custom_regex_replace
        if pat:
            series = series.str.replace(pat, repl, regex=True)

    df.loc[mask, column] = series

    # If requested, convert empty and whitespace-only strings to NaN
    if empty_to_null:
        empty_mask = df.loc[mask, column].astype(str).str.strip() == ""
        empty_indices = df.loc[mask, column][empty_mask].index
        if len(empty_indices) > 0:
            df.loc[empty_indices, column] = np.nan

    # Calculate modified count (comparing string representations and NaN status)
    changed_mask = (original_series.isna() != df[column].isna()) | (
        mask & df[column].notna() & (original_series.astype(str) != df[column].astype(str))
    )
    changes_count = int(changed_mask.sum())

    return df, changes_count


def clean_all_string_columns(df: pd.DataFrame, empty_to_null: bool = True) -> Tuple[pd.DataFrame, int]:
    """Applies whitespace trimming, extra space collapsing, and empty-to-null to all string columns."""
    df = df.copy()
    total_changes = 0

    # Include string/object columns
    cols = [c for c in df.columns if df[c].dtype == "object" or str(df[c].dtype) == "string" or pd.api.types.is_string_dtype(df[c])]
    for col in cols:
        df, changes = clean_string_column(
            df,
            col,
            trim_whitespace=True,
            remove_extra_spaces=True,
            empty_to_null=empty_to_null,
        )
        total_changes += changes

    return df, total_changes

