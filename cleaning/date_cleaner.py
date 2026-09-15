"""
Date Cleaning Engine.
Parses heterogeneous and messy date formats into standardized date/datetime formats.
"""

import re
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
from dateutil import parser as date_parser


FORMAT_MAP = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "DD Mon YYYY": "%d %b %Y",
    "YYYY-MM-DD HH:MM:SS": "%Y-%m-%d %H:%M:%S",
}


def clean_date_column(
    df: pd.DataFrame,
    column: str,
    input_format: Optional[str] = None,  # e.g., 'DD/MM/YYYY' or None for auto-detect
    output_format: str = "YYYY-MM-DD",  # key in FORMAT_MAP or custom strftime
    day_first: bool = True,
) -> Tuple[pd.DataFrame, int, List[Dict[str, Any]]]:
    """
    Standardizes a date column.
    Returns:
        (updated_df, converted_count, unparseable_records)
    """
    if column not in df.columns:
        return df, 0, []

    df = df.copy()
    original_series = df[column].copy()
    mask = df[column].notna()

    target_strftime = FORMAT_MAP.get(output_format, output_format)
    input_strftime = FORMAT_MAP.get(input_format) if input_format else None

    unparseable = []
    converted_values = []
    converted_count = 0

    for idx in df[mask].index:
        orig_val = original_series[idx]
        val_str = str(orig_val).strip()
        if not val_str or val_str.lower() in ("nan", "nat", "null", "none"):
            converted_values.append(None)
            continue

        parsed_dt = None

        # 1. Try explicit input format if provided
        if input_strftime:
            try:
                parsed_dt = pd.to_datetime(val_str, format=input_strftime)
            except Exception:
                pass

        # 2. ISO / YYYY-first dates should never use dayfirst=True
        if parsed_dt is None and re.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", val_str):
            try:
                parsed_dt = pd.to_datetime(val_str, dayfirst=False)
            except Exception:
                pass

        # 3. Try standard pd.to_datetime with user's dayfirst setting
        if parsed_dt is None:
            try:
                parsed_dt = pd.to_datetime(val_str, dayfirst=day_first)
            except Exception:
                pass

        # 4. Try dateutil parser as flexible fallback
        if parsed_dt is None:
            effective_day_first = False if re.match(r"^\d{4}", val_str) else day_first
            try:
                parsed_dt = date_parser.parse(val_str, dayfirst=effective_day_first)
            except Exception:
                pass

        if parsed_dt is not None:
            try:
                formatted_str = parsed_dt.strftime(target_strftime)
                converted_values.append(formatted_str)
                if formatted_str != val_str:
                    converted_count += 1
            except Exception:
                converted_values.append(val_str)
        else:
            unparseable.append({
                "row_index": int(idx),
                "original_value": val_str,
                "reason": "Could not parse date with specified rules",
            })
            converted_values.append(val_str)

    df.loc[mask, column] = converted_values
    return df, converted_count, unparseable[:50]
