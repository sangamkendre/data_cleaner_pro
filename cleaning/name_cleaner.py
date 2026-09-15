"""
Name Sanitizer & Cleaner Engine.
Ensures name attributes (e.g. Last_Name, First_Name, Name) contain only alphabetic
characters, stripping all special characters, symbols, digits, and extra whitespace,
and formatting to standard Title Case.
"""

import re
from typing import Tuple, Optional
import pandas as pd


def clean_name_column(
    df: pd.DataFrame,
    column: str,
    alphabets_only: bool = True,
    case_transform: Optional[str] = "title",  # 'title', 'upper', 'lower', None
    allow_spaces: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """
    Sanitizes a name column so values contain only alphabetic characters.
    Handles noisy prefixes/suffixes (e.g. /White -> White, ...Potter -> Potter, Flenderson_ -> Flenderson),
    embedded numbers, and multiple spaces.
    
    Returns:
        (updated_df, modified_count)
    """
    if column not in df.columns:
        return df, 0

    df = df.copy()
    original_series = df[column].copy()

    mask = df[column].notna()
    series = df.loc[mask, column].astype(str)

    if alphabets_only:
        # Step 1: Replace common delimiter symbols (underscores, slashes, hyphens) between words with space
        # e.g. "Mary_Jane" -> "Mary Jane", "/White" -> " White", "Flenderson_" -> "Flenderson "
        series = series.str.replace(r"[_\-/]+", " ", regex=True)

        # Step 2: Strip all non-alphabetic characters (keep only letters and spaces)
        if allow_spaces:
            series = series.str.replace(r"[^a-zA-Z\s]", "", regex=True)
        else:
            series = series.str.replace(r"[^a-zA-Z]", "", regex=True)

    # Step 3: Collapse repeated internal spaces and trim whitespace
    series = series.str.replace(r"\s+", " ", regex=True).str.strip()

    # Step 4: Casing transformation
    if case_transform == "title":
        series = series.str.title()
    elif case_transform == "upper":
        series = series.str.upper()
    elif case_transform == "lower":
        series = series.str.lower()

    df.loc[mask, column] = series

    # Calculate modifications
    changed_mask = mask & (original_series.astype(str) != df[column].astype(str))
    changes_count = int(changed_mask.sum())

    return df, changes_count
