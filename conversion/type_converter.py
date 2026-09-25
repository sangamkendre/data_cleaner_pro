"""
Data Type Conversion Engine.
Converts column data types safely and reports problematic/unconvertible values.
"""

import re
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
import numpy as np


def inspect_or_convert_type(
    df: pd.DataFrame,
    column: str,
    target_type: str,  # 'Integer', 'Float', 'String', 'Boolean', 'Date', 'Datetime'
    apply_fix: bool = False,
    clean_currency_symbols: bool = True,
    fill_unconvertible: Optional[Any] = None,  # if None, keeps as NaN or coerces
    case_transform: Optional[str] = None,  # 'lower', 'upper', 'title', 'capitalize', None
    trim_whitespace: bool = True,
    collapse_spaces: bool = False,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], int]:
    """
    Inspects and optionally converts a column to target_type.
    Detects and reports problematic values (e.g., '₹50,000', 'N/A', 'unknown').
    Supports casing transformation (upper, lower, title, capitalize) and whitespace sanitization when target_type is String.
    Returns:
        (df, problematic_records, converted_count)
    """
    if column not in df.columns:
        return df, [], 0

    df = df.copy()
    original_series = df[column].copy()
    mask = df[column].notna()

    problematic = []
    converted_count = 0
    clean_target = target_type.capitalize()

    if clean_target in ("Integer", "Float"):
        # Detect currency or comma symbols
        str_series = df.loc[mask, column].astype(str)
        cleaned_str = str_series
        if clean_currency_symbols:
            cleaned_str = str_series.str.replace(r"[₹$,€£ ]", "", regex=True)

        # Test conversion
        numeric_series = pd.to_numeric(cleaned_str, errors="coerce")
        failed_mask = mask & numeric_series.isna()

        if failed_mask.any():
            for idx in df[failed_mask].head(50).index:
                val = original_series[idx]
                problematic.append({
                    "row_index": int(idx),
                    "original_value": str(val),
                    "reason": "Non-numeric characters present",
                })

        if apply_fix:
            if clean_target == "Integer":
                # Convert to nullable Int64
                df[column] = pd.to_numeric(cleaned_str, errors="coerce").round().astype("Int64")
            else:
                df[column] = pd.to_numeric(cleaned_str, errors="coerce")

            if fill_unconvertible is not None and df[column].isna().any():
                df[column] = df[column].fillna(fill_unconvertible)

            converted_count = int(mask.sum() - len(problematic))

    elif clean_target in ("Date", "Datetime"):
        datetime_series = pd.to_datetime(df[column], errors="coerce")
        failed_mask = mask & datetime_series.isna()

        if failed_mask.any():
            for idx in df[failed_mask].head(50).index:
                val = original_series[idx]
                problematic.append({
                    "row_index": int(idx),
                    "original_value": str(val),
                    "reason": "Invalid or unparseable date format",
                })

        if apply_fix:
            if clean_target == "Date":
                df[column] = datetime_series.dt.strftime("%Y-%m-%d")
            else:
                df[column] = datetime_series
            converted_count = int(mask.sum() - len(problematic))

    elif clean_target == "Boolean":
        bool_map = {
            "true": True, "1": True, "yes": True, "y": True, "t": True,
            "false": False, "0": False, "no": False, "n": False, "f": False,
        }
        str_series = df.loc[mask, column].astype(str).str.strip().str.lower()
        mapped = str_series.map(bool_map)
        failed_mask = mask & mapped.isna()

        if failed_mask.any():
            for idx in df[failed_mask].head(50).index:
                val = original_series[idx]
                problematic.append({
                    "row_index": int(idx),
                    "original_value": str(val),
                    "reason": "Cannot be evaluated as true/false",
                })

        if apply_fix:
            df[column] = mapped.astype("boolean")
            converted_count = int(mask.sum() - len(problematic))

    elif clean_target == "String":
        str_series = df.loc[mask, column].astype(str)
        if trim_whitespace:
            str_series = str_series.str.strip()
        if collapse_spaces:
            str_series = str_series.str.replace(r"\s+", " ", regex=True)

        if case_transform == "lower":
            str_series = str_series.str.lower()
        elif case_transform == "upper":
            str_series = str_series.str.upper()
        elif case_transform == "title":
            str_series = str_series.str.title()
        elif case_transform == "capitalize":
            str_series = str_series.str.capitalize()

        converted_count = int(mask.sum())

        if apply_fix:
            df[column] = df[column].astype(str)
            df.loc[mask, column] = str_series
            df.loc[original_series.isna(), column] = np.nan

    return df, problematic, converted_count


def preview_string_transformation(
    df: pd.DataFrame,
    column: str,
    case_transform: Optional[str] = None,
    trim_whitespace: bool = True,
    collapse_spaces: bool = False,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Returns before/after preview samples for string transformation."""
    if column not in df.columns:
        return []
    mask = df[column].notna()
    if not mask.any():
        return []

    sample_indices = df[mask].head(limit).index
    preview = []
    for idx in sample_indices:
        orig = str(df.loc[idx, column])
        transformed = orig
        if trim_whitespace:
            transformed = transformed.strip()
        if collapse_spaces:
            transformed = re.sub(r"\s+", " ", transformed)
        if case_transform == "lower":
            transformed = transformed.lower()
        elif case_transform == "upper":
            transformed = transformed.upper()
        elif case_transform == "title":
            transformed = transformed.title()
        elif case_transform == "capitalize":
            transformed = transformed.capitalize()

        preview.append({
            "row_index": int(idx),
            "original_value": orig,
            "transformed_value": transformed,
            "changed": (orig != transformed),
        })
    return preview

