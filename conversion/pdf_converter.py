"""
PDF Table Extractor & Converter Module.
Extracts structured tables from PDF files using pdfplumber and converts them
into pandas DataFrames, Excel (.xlsx), or CSV (.csv) files.
"""

import os
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def _clean_header_value(val: Any, index: int) -> str:
    """Cleans a header cell string, stripping whitespace and newlines."""
    if val is None:
        return f"Column_{index + 1}"
    text = str(val).replace("\r", " ").replace("\n", " ").strip()
    return text if text else f"Column_{index + 1}"


def _clean_cell_value(val: Any) -> Any:
    """Cleans a data cell string, normalizing whitespace and newlines."""
    if val is None:
        return None
    if isinstance(val, str):
        cleaned = val.replace("\r", " ").replace("\n", " ").strip()
        import re
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned if cleaned else None
    return val


def table_to_dataframe(table_rows: List[List[Any]]) -> pd.DataFrame:
    """
    Converts a raw table extracted by pdfplumber into a clean pandas DataFrame.
    The first row is treated as the column header.
    """
    if not table_rows or len(table_rows) == 0:
        return pd.DataFrame()

    raw_header = table_rows[0]
    data_rows = table_rows[1:] if len(table_rows) > 1 else []

    # Clean headers and ensure uniqueness
    headers = []
    seen = {}
    for i, h in enumerate(raw_header):
        cleaned_h = _clean_header_value(h, i)
        if cleaned_h in seen:
            seen[cleaned_h] += 1
            headers.append(f"{cleaned_h}_{seen[cleaned_h]}")
        else:
            seen[cleaned_h] = 0
            headers.append(cleaned_h)

    num_cols = len(headers)
    cleaned_rows = []
    for row in data_rows:
        cleaned_row = []
        for i in range(num_cols):
            cell = row[i] if i < len(row) else None
            cleaned_row.append(_clean_cell_value(cell))
        cleaned_rows.append(cleaned_row)

    df = pd.DataFrame(cleaned_rows, columns=headers)
    return df


def inspect_pdf_tables(file_path: str) -> Dict[str, Any]:
    """
    Inspects a PDF file and returns detailed metadata about pages and tables detected.
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber is required for PDF table extraction. Run: pip install pdfplumber")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    tables_info = []
    total_pages = 0

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages, start=1):
            extracted = page.extract_tables()
            for tbl_idx, raw_table in enumerate(extracted, start=1):
                if not raw_table or len(raw_table) == 0:
                    continue
                df = table_to_dataframe(raw_table)
                # Preview top 5 rows
                preview_records = df.head(5).replace({np.nan: None}).to_dict(orient="records")

                table_id = f"page_{page_idx}_table_{tbl_idx}"
                table_name = f"Page {page_idx} - Table {tbl_idx}"

                tables_info.append({
                    "id": table_id,
                    "name": table_name,
                    "page_number": page_idx,
                    "table_index": tbl_idx,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns),
                    "preview": preview_records,
                })

    return {
        "file_name": os.path.basename(file_path),
        "total_pages": total_pages,
        "total_tables": len(tables_info),
        "tables": tables_info,
        "has_extractable_data": len(tables_info) > 0,
    }


def extract_pdf_tables_to_df(
    file_path: str,
    table_selection: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Reads tabular data from a PDF file into a single pandas DataFrame.

    table_selection can be:
        - None or 'all' or 'combined': Merges/concatenates all tables across pages.
        - 'page_X_table_Y' or 'Page X - Table Y': Selects a specific table.
        - 'Page X': Selects all tables on Page X.
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber is not installed.")

    tables_data: List[Tuple[str, pd.DataFrame]] = []
    total_pages = 0

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages, start=1):
            extracted = page.extract_tables()
            for tbl_idx, raw_table in enumerate(extracted, start=1):
                if not raw_table or len(raw_table) == 0:
                    continue
                df = table_to_dataframe(raw_table)
                table_name = f"Page {page_idx} - Table {tbl_idx}"
                tables_data.append((table_name, df))

    if not tables_data:
        raise ValueError(
            "No extractable tables were found in the uploaded PDF. "
            "Please ensure the document contains structured tabular data."
        )

    available_sheets = [t[0] for t in tables_data]
    if len(tables_data) > 1:
        available_sheets.insert(0, "All Tables (Combined)")

    # Determine selection
    selected_name = table_selection
    if not selected_name:
        selected_name = "All Tables (Combined)" if len(tables_data) > 1 else tables_data[0][0]

    final_df: pd.DataFrame
    if selected_name in ("All Tables (Combined)", "all", "combined"):
        dfs_to_combine = [t[1] for t in tables_data if len(t[1]) > 0]
        if dfs_to_combine:
            final_df = pd.concat(dfs_to_combine, ignore_index=True)
        else:
            final_df = tables_data[0][1]
    else:
        # Match specific table
        matched = None
        for name, df in tables_data:
            if name.lower() == selected_name.lower():
                matched = df
                break
        if matched is None:
            # Fallback to first table
            matched = tables_data[0][1]
            selected_name = tables_data[0][0]
        final_df = matched

    metadata = {
        "format": "PDF",
        "total_pages": total_pages,
        "total_tables": len(tables_data),
        "sheets": available_sheets,
        "selected_sheet": selected_name,
        "rows": len(final_df),
        "columns": len(final_df.columns),
    }

    return final_df, metadata


def convert_pdf_to_export_file(
    file_path: str,
    output_format: str = "xlsx",
    table_selection: Optional[str] = None,
    output_path: Optional[str] = None
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Converts a PDF table into an Excel (.xlsx) or CSV (.csv) file directly.

    Returns:
        Tuple[str, str, Dict[str, Any]]: (output_filepath, download_filename, summary_metadata)
    """
    df, meta = extract_pdf_tables_to_df(file_path, table_selection=table_selection)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_format = output_format.lower().strip()
    if output_format in ("excel", "xlsx"):
        out_ext = ".xlsx"
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        out_ext = ".csv"
        mime = "text/csv"

    out_name = f"{base_name}_converted{out_ext}"
    if not output_path:
        out_dir = os.path.dirname(file_path)
        output_path = os.path.join(out_dir, out_name)

    if out_ext == ".xlsx":
        df.to_excel(output_path, index=False, engine="openpyxl")
    else:
        df.to_csv(output_path, index=False)

    meta.update({
        "output_path": output_path,
        "download_name": out_name,
        "mime_type": mime,
        "output_format": output_format,
    })

    return output_path, out_name, meta
