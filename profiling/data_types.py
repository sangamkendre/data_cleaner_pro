"""
Data Type Detection & Mismatch Profiler.
Analyzes column types, identifies semantic mismatches (e.g. dates, numbers, contact, email stored as strings),
and flags actionable issues.
"""

import re
from typing import Dict, Any, List
import pandas as pd
import numpy as np


def detect_column_types(df: pd.DataFrame) -> List[Dict[str, Any]]:
    results = []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna().astype(str).str.strip()
        non_null_count = len(non_null)
        raw_dtype = str(series.dtype)

        # Baseline detected type
        detected_type = "String"
        status = "✓"
        issue = None
        suggested_type = None
        action = None
        has_whitespace = False

        if "int" in raw_dtype.lower():
            detected_type = "Integer"
        elif "float" in raw_dtype.lower():
            detected_type = "Float"
        elif "bool" in raw_dtype.lower():
            detected_type = "Boolean"
        elif "datetime" in raw_dtype.lower():
            detected_type = "Date"
        else:
            # It's an object / string column. Check semantic content!
            if non_null_count > 0:
                sample = non_null.head(100)
                raw_sample = series.dropna().astype(str).head(100)
                has_whitespace = any(s != s.strip() or "  " in s for s in raw_sample)
                col_name_lower = str(col).lower()

                # 1. Check for Email
                is_email_col_name = any(k in col_name_lower for k in ["email", "e-mail", "mail"])
                email_match_count = sum(1 for s in sample if "@" in s and "." in s)
                if is_email_col_name or (email_match_count / len(sample) >= 0.5):
                    detected_type = "Email"
                    # Check for issues: uppercase, leading/trailing/inner spaces, common typos
                    has_email_issues = any(
                        s != s.lower()
                        or " " in s
                        or any(t in s.lower() for t in ["@gmai.", "@gamil.", "@gmial.", "@yaho.", "@hotmial."])
                        or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", s.strip())
                        for s in raw_sample
                    )
                    if has_email_issues:
                        status = "⚠"
                        issue = "Email column with formatting issues, typos, or casing"
                        suggested_type = "Clean Email"
                        action = "Clean Email"

                # 2. Check for Date patterns
                elif (
                    any(k in col_name_lower for k in ["date", "dob", "birth", "joined", "created", "timestamp", "time"])
                    or sum(1 for s in sample if re.match(r"^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$", s)) / len(sample) >= 0.5
                ):
                    detected_type = "Date"
                    status = "⚠"
                    issue = "Dates stored as String"
                    suggested_type = "Date"
                    action = "Fix Date"

                # 3. Check for Contact / Phone
                elif (
                    any(k in col_name_lower for k in ["contact", "phone", "mobile", "cell", "tel"])
                    or sum(1 for s in sample if re.search(r"\d{7,}", re.sub(r"[^0-9]", "", s))) / len(sample) >= 0.6
                ):
                    detected_type = "Phone"
                    has_noise = any(re.search(r"[^\d+]", s) or re.search(r"[a-zA-Z]", s) for s in sample)
                    if has_noise:
                        status = "⚠"
                        issue = "Phone numbers with noisy symbols/spaces"
                        suggested_type = "Clean Phone"
                        action = "Clean Contact"

                # 4. Check for Name columns (e.g. Last_Name, First_Name, Name)
                elif (
                    any(k in col_name_lower for k in ["name", "fname", "lname", "first_name", "last_name", "full_name", "surname", "author", "person", "customer_name"])
                ):
                    detected_type = "Name"
                    has_special_chars = any(
                        re.search(r"[^a-zA-Z\s]", s) for s in raw_sample
                    )
                    has_casing_issue = any(
                        s.strip() != s.strip().title() for s in raw_sample if len(s.strip()) > 1
                    )
                    if has_special_chars:
                        status = "⚠"
                        issue = "Name column contains special characters or digits (e.g. /, ..., _, 0-9)"
                        suggested_type = "Clean Name"
                        action = "Clean Names"
                    elif has_whitespace or has_casing_issue:
                        status = "⚠"
                        issue = "Names with irregular whitespace or casing"
                        suggested_type = "Clean Name"
                        action = "Clean Names"

                # 5. Check for Numeric disguised as String (with currency symbols, commas, or slight errors)
                else:
                    cleaned_nums = sample.str.replace(r"[₹$,€£ ]", "", regex=True)
                    numeric_successes = pd.to_numeric(cleaned_nums, errors="coerce").notna().sum()
                    if numeric_successes / len(sample) >= 0.7:
                        has_decimals = any("." in s for s in sample if pd.to_numeric(s.replace(",", ""), errors="coerce") is not np.nan)
                        target_type = "Float" if has_decimals else "Integer"
                        status = "⚠"
                        issue = f"Contains numeric values stored as text ({target_type})"
                        suggested_type = target_type
                        action = f"Convert to {target_type}"
                    elif has_whitespace:
                        status = "⚠"
                        issue = "Extra spaces or leading/trailing whitespace"
                        suggested_type = "String"
                        action = "Trim Spaces"

        results.append({
            "column": col,
            "raw_dtype": raw_dtype,
            "detected_type": detected_type,
            "status": status,
            "issue": issue,
            "suggested_type": suggested_type,
            "action": action,
            "has_whitespace": has_whitespace,
        })

    return results
