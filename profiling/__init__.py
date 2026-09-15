"""
Data Profiling Package.
Combines file overview, data type detection, duplicate analysis, null analysis, and quality scoring.
"""

from profiling.file_info import get_file_info
from profiling.data_types import detect_column_types
from profiling.duplicates import analyze_duplicates
from profiling.null_analysis import analyze_nulls
from profiling.quality_scorer import compute_quality_score


def profile_dataset(df, file_path=None, filename=None, file_type="Unknown"):
    """Runs complete profiling pipeline on the dataset."""
    info = get_file_info(df, file_path, filename, file_type)
    null_info = analyze_nulls(df)
    dup_info = analyze_duplicates(df)
    type_info = detect_column_types(df)
    quality = compute_quality_score(df, null_info, dup_info, type_info)

    return {
        "file_info": info,
        "null_analysis": null_info,
        "duplicate_analysis": dup_info,
        "data_types": type_info,
        "quality": quality,
    }


__all__ = [
    "get_file_info",
    "detect_column_types",
    "analyze_duplicates",
    "analyze_nulls",
    "compute_quality_score",
    "profile_dataset",
]
