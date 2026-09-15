"""
Contact & Phone Number Cleaning Engine.
Removes noise, non-digit characters, and standardizes contact numbers.
"""

import re
from typing import Tuple, Dict, Any, List
import pandas as pd


def clean_contact_column(
    df: pd.DataFrame,
    column: str,
    strip_non_digits: bool = True,
    normalize_10_digits: bool = False,
    format_style: str = "digits_only",  # 'digits_only', 'hyphenated', 'international'
    country_code: str = "91",
) -> Tuple[pd.DataFrame, int, List[Dict[str, Any]]]:
    """
    Cleans contact numbers in the specified column.
    Returns:
        (updated_df, cleaned_count, invalid_entries)
    """
    if column not in df.columns:
        return df, 0, []

    df = df.copy()
    original_series = df[column].copy()
    mask = df[column].notna()

    # Step 1: Extract digits
    cleaned_series = df.loc[mask, column].astype(str)
    if strip_non_digits:
        cleaned_series = cleaned_series.str.replace(r"[^0-9]", "", regex=True)

    invalid_entries = []

    def format_number(val: str, original_val: Any, row_idx: int) -> str:
        if not val or val == "nan":
            return ""

        digits = val
        # Optional 10-digit normalization
        if normalize_10_digits:
            if digits.startswith(country_code) and len(digits) == 10 + len(country_code):
                digits = digits[len(country_code):]
            elif digits.startswith("0") and len(digits) == 11:
                digits = digits[1:]

        # Check if suspicious length
        if len(digits) < 7 or len(digits) > 15:
            invalid_entries.append({
                "row_index": int(row_idx),
                "original": str(original_val),
                "cleaned": digits,
                "reason": f"Unusual digit length ({len(digits)})",
            })

        if format_style == "hyphenated" and len(digits) == 10:
            return f"{digits[:5]}-{digits[5:]}"
        elif format_style == "international" and len(digits) >= 10:
            if len(digits) == 10:
                return f"+{country_code} {digits[:5]} {digits[5:]}"
            elif digits.startswith(country_code):
                sub = digits[len(country_code):]
                return f"+{country_code} {sub[:5]} {sub[5:]}"

        return digits

    formatted_values = []
    for idx, (clean_val, orig_val) in enumerate(zip(cleaned_series, original_series[mask])):
        formatted_values.append(format_number(clean_val, orig_val, mask[mask].index[idx]))

    df.loc[mask, column] = formatted_values

    # Count how many changed
    changed_mask = mask & (original_series.astype(str) != df[column].astype(str))
    cleaned_count = int(changed_mask.sum())

    return df, cleaned_count, invalid_entries[:50]
