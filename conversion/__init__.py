"""
Conversion Package.
Combines type converter and parquet exporter.
"""

from conversion.type_converter import inspect_or_convert_type, preview_string_transformation
from conversion.parquet_exporter import export_to_parquet
from conversion.pdf_converter import (
    inspect_pdf_tables,
    extract_pdf_tables_to_df,
    convert_pdf_to_export_file,
    table_to_dataframe,
)

__all__ = [
    "inspect_or_convert_type",
    "preview_string_transformation",
    "export_to_parquet",
    "inspect_pdf_tables",
    "extract_pdf_tables_to_df",
    "convert_pdf_to_export_file",
    "table_to_dataframe",
]

