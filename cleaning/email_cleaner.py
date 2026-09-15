"""
Email Cleaning Engine.
Validates, standardizes, normalizes, and fixes common email typos and formatting issues.
"""

import re
from typing import Tuple, Dict, Any, List
import pandas as pd

# Common domain typos and their corrections
DOMAIN_FIXES = {
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmaik.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yaho.co.in": "yahoo.co.in",
    "hotmial.com": "hotmail.com",
    "hotmaill.com": "hotmail.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
}

# Standard email regex pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


def clean_email_column(
    df: pd.DataFrame,
    column: str,
    lowercase: bool = True,
    trim_spaces: bool = True,
    remove_inner_spaces: bool = True,
    fix_domain_typos: bool = True,
) -> Tuple[pd.DataFrame, int, List[Dict[str, Any]]]:
    """
    Cleans email addresses in the specified column.
    Returns:
        (updated_df, cleaned_count, invalid_emails_report)
    """
    if column not in df.columns:
        return df, 0, []

    df = df.copy()
    original_series = df[column].copy()
    mask = df[column].notna()

    cleaned_values = []
    invalid_entries = []
    cleaned_count = 0

    for idx in df[mask].index:
        orig_val = original_series[idx]
        val_str = str(orig_val)

        if not val_str or val_str.lower() in ("nan", "null", "none", "n/a"):
            cleaned_values.append(val_str)
            continue

        email = val_str
        if trim_spaces:
            email = email.strip()

        if remove_inner_spaces:
            email = re.sub(r"\s+", "", email)

        if lowercase:
            email = email.lower()

        # Fix domain typos if applicable
        if fix_domain_typos and "@" in email:
            parts = email.split("@", 1)
            local_part = parts[0]
            domain_part = parts[1]
            if domain_part in DOMAIN_FIXES:
                email = f"{local_part}@{DOMAIN_FIXES[domain_part]}"

        # Validate against standard pattern
        is_valid = bool(EMAIL_REGEX.match(email))
        if not is_valid:
            reason = "Missing '@' symbol" if "@" not in email else (
                "Missing domain extension (e.g. .com)" if "." not in email.split("@")[-1] else "Invalid email characters/syntax"
            )
            invalid_entries.append({
                "row_index": int(idx),
                "original": str(orig_val),
                "cleaned": email,
                "reason": reason,
            })

        if email != val_str:
            cleaned_count += 1

        cleaned_values.append(email)

    df.loc[mask, column] = cleaned_values

    return df, cleaned_count, invalid_entries[:50]
