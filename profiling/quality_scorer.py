"""
Data Quality Scorer.
Computes composite quality score (0 - 100%) and health indicators.
"""

from typing import Dict, Any, List
import pandas as pd


def compute_quality_score(
    df: pd.DataFrame,
    null_info: Dict[str, Any],
    dup_info: Dict[str, Any],
    type_info: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_rows = len(df)
    total_cols = len(df.columns)

    if total_rows == 0 or total_cols == 0:
        return {
            "score": 100,
            "grade": "N/A",
            "completeness_score": 100,
            "uniqueness_score": 100,
            "type_integrity_score": 100,
            "columns_with_issues": 0,
            "issues_summary": [],
        }

    # 1. Completeness Score (0-100)
    null_pct = null_info.get("overall_null_percentage", 0.0)
    completeness = max(0.0, 100.0 - (null_pct * 2.5))  # Nulls weight

    # 2. Uniqueness Score (0-100)
    dup_pct = dup_info.get("duplicate_percentage", 0.0)
    uniqueness = max(0.0, 100.0 - (dup_pct * 3.0))

    # 3. Type & Cleanliness Integrity (0-100)
    issues = [t for t in type_info if t.get("status") == "⚠"]
    issues_count = len(issues)
    type_integrity = max(0.0, 100.0 - ((issues_count / total_cols) * 50.0))

    # Composite weighted score:
    # 40% Completeness, 30% Uniqueness, 30% Type/Cleanliness
    composite = (completeness * 0.40) + (uniqueness * 0.30) + (type_integrity * 0.30)
    score = int(round(max(0, min(100, composite))))

    if score >= 90:
        grade = "Excellent"
        color = "emerald"
    elif score >= 75:
        grade = "Good"
        color = "blue"
    elif score >= 60:
        grade = "Fair"
        color = "amber"
    else:
        grade = "Needs Attention"
        color = "rose"

    return {
        "score": score,
        "grade": grade,
        "color": color,
        "completeness_score": round(completeness, 1),
        "uniqueness_score": round(uniqueness, 1),
        "type_integrity_score": round(type_integrity, 1),
        "columns_with_issues": issues_count,
        "total_issues": issues_count + (1 if dup_info.get("duplicate_rows", 0) > 0 else 0) + (1 if null_info.get("total_nulls", 0) > 0 else 0),
    }
