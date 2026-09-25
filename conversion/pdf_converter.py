"""
PDF Table Extractor & Converter Module.
Extracts structured tables from PDF files using pdfplumber and converts them
into pandas DataFrames, multi-sheet Excel (.xlsx), or CSV (.csv) files.
Intelligently distinguishes between matching schemas (multi-page tables)
and different schemas (heterogeneous tables).
"""

import os
import io
import re
import zipfile
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


def _generate_table_name(page_idx: int, tbl_idx: int, df: pd.DataFrame) -> str:
    """Generates a human-friendly descriptive name for an extracted table."""
    meaningful = [
        c for c in df.columns
        if not c.startswith("Column_") and len(c.strip()) > 1
    ]
    if meaningful:
        tag = meaningful[0].split("(")[0].strip()[:18].strip()
        if tag:
            return f"Page {page_idx} - Table {tbl_idx} ({tag})"
    return f"Page {page_idx} - Table {tbl_idx}"


def check_columns_match(tables_data: List[Tuple[str, pd.DataFrame]]) -> bool:
    """Returns True if all extracted tables share identical column signatures."""
    if len(tables_data) <= 1:
        return True
    first_cols = list(tables_data[0][1].columns)
    for _, df in tables_data[1:]:
        if list(df.columns) != first_cols:
            return False
    return True


def sanitize_excel_sheet_name(name: str, index: int, seen: set) -> str:
    """Sanitizes sheet names to conform to Excel's 31-character limit and character rules."""
    invalid = set(r"[]:*?/\x5c")
    cleaned = "".join(c for c in name if c not in invalid).strip()
    if not cleaned:
        cleaned = f"Table_{index + 1}"
    truncated = cleaned[:31].strip()
    if truncated in seen:
        truncated = f"{truncated[:27]}_{index + 1}"
    seen.add(truncated)
    return truncated


def inspect_pdf_tables(file_path: str) -> Dict[str, Any]:
    """
    Inspects a PDF file and returns detailed metadata about pages and tables detected,
    including column compatibility across tables.
    """
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber is required for PDF table extraction. Run: pip install pdfplumber")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    tables_info = []
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
                if df.empty:
                    continue

                table_name = _generate_table_name(page_idx, tbl_idx, df)
                table_id = f"page_{page_idx}_table_{tbl_idx}"
                tables_data.append((table_name, df))

                # Preview top 5 rows
                preview_records = df.head(5).replace({np.nan: None}).to_dict(orient="records")

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

    columns_match = check_columns_match(tables_data)

    return {
        "file_name": os.path.basename(file_path),
        "total_pages": total_pages,
        "total_tables": len(tables_info),
        "tables": tables_info,
        "columns_match": columns_match,
        "has_extractable_data": len(tables_info) > 0,
    }


def extract_pdf_tables_to_df(
    file_path: str,
    table_selection: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Reads tabular data from a PDF file into a pandas DataFrame.
    When multiple tables have different columns, defaults to Table 1 instead of
    generating an incongruous sparse combined table.
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
                if df.empty:
                    continue
                table_name = _generate_table_name(page_idx, tbl_idx, df)
                tables_data.append((table_name, df))

    if not tables_data:
        raise ValueError(
            "No extractable tables were found in the uploaded PDF. "
            "Please ensure the document contains structured tabular data."
        )

    columns_match = check_columns_match(tables_data)
    individual_sheets = [t[0] for t in tables_data]

    # Available sheets construction
    available_sheets: List[str] = []
    if columns_match and len(tables_data) > 1:
        # Tables have identical columns (e.g. multi-page report)
        available_sheets.append("All Tables (Combined)")
        available_sheets.extend(individual_sheets)
    else:
        # Heterogeneous tables with different column schemas
        available_sheets.extend(individual_sheets)
        if len(tables_data) > 1:
            available_sheets.append("All Tables (Union / Disjointed)")

    # Selection determination
    selected_name = table_selection
    if not selected_name:
        if columns_match and len(tables_data) > 1:
            selected_name = "All Tables (Combined)"
        else:
            # Default to the first individual table when schemas differ!
            selected_name = tables_data[0][0]

    final_df: pd.DataFrame
    if selected_name in ("All Tables (Combined)", "All Tables (Union / Disjointed)", "all", "combined"):
        dfs_to_combine = [t[1] for t in tables_data if len(t[1]) > 0]
        final_df = pd.concat(dfs_to_combine, ignore_index=True) if dfs_to_combine else tables_data[0][1]
    else:
        matched = None
        for name, df in tables_data:
            # Match by full name or ID or simple prefix
            if name.lower() == selected_name.lower() or selected_name.lower() in name.lower():
                matched = df
                selected_name = name
                break
        if matched is None:
            matched = tables_data[0][1]
            selected_name = tables_data[0][0]
        final_df = matched

    tables_dict = {name: df.copy() for name, df in tables_data}

    metadata = {
        "format": "PDF",
        "total_pages": total_pages,
        "total_tables": len(tables_data),
        "sheets": available_sheets,
        "selected_sheet": selected_name,
        "columns_match": columns_match,
        "tables_data": tables_dict,
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
    Converts PDF table(s) into an Excel (.xlsx), CSV (.csv), or ZIP (.zip of CSVs).
    When multiple tables have different columns and output is Excel, writes each table
    to its own sheet in the workbook!
    """
    df, meta = extract_pdf_tables_to_df(file_path, table_selection=table_selection)
    tables_dict: Dict[str, pd.DataFrame] = meta.get("tables_data", {})
    columns_match: bool = meta.get("columns_match", True)
    total_tables: int = meta.get("total_tables", 1)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_format = output_format.lower().strip()
    is_excel = output_format in ("excel", "xlsx")

    # Determine if user wants all tables exported
    is_all_tables = (
        not table_selection
        or table_selection in ("all", "combined", "all_sheets", "All Tables (Combined)", "All Tables (Union / Disjointed)")
    )

    if is_excel:
        out_ext = ".xlsx"
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        out_name = f"{base_name}_converted.xlsx"
        if not output_path:
            out_dir = os.path.dirname(file_path)
            output_path = os.path.join(out_dir, out_name)

        if is_all_tables and not columns_match and total_tables > 1:
            # MULTI-SHEET WORKBOOK: Write each table to its own Excel sheet!
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                seen_sheets = set()
                for i, (tbl_name, df_tbl) in enumerate(tables_dict.items()):
                    sheet_title = sanitize_excel_sheet_name(tbl_name, i, seen_sheets)
                    df_tbl.to_excel(writer, sheet_name=sheet_title, index=False)
        else:
            # Single sheet export or unified multi-page table
            df.to_excel(output_path, index=False, engine="openpyxl")

    else:
        # CSV handling
        if is_all_tables and not columns_match and total_tables > 1:
            # Different schemas: Export all individual tables bundled into a clean ZIP archive!
            out_ext = ".zip"
            mime = "application/zip"
            out_name = f"{base_name}_tables_csv.zip"
            if not output_path:
                out_dir = os.path.dirname(file_path)
                output_path = os.path.join(out_dir, out_name)

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
                seen_files = set()
                for i, (tbl_name, df_tbl) in enumerate(tables_dict.items()):
                    clean_name = re.sub(r"[^\w\s-]", "", tbl_name).strip().replace(" ", "_")
                    file_name = f"{clean_name}.csv"
                    if file_name in seen_files:
                        file_name = f"{clean_name}_{i+1}.csv"
                    seen_files.add(file_name)

                    csv_buffer = io.StringIO()
                    df_tbl.to_csv(csv_buffer, index=False)
                    zip_out.writestr(file_name, csv_buffer.getvalue())
        else:
            out_ext = ".csv"
            mime = "text/csv"
            out_name = f"{base_name}_converted.csv"
            if not output_path:
                out_dir = os.path.dirname(file_path)
                output_path = os.path.join(out_dir, out_name)
            df.to_csv(output_path, index=False)

    meta.update({
        "output_path": output_path,
        "download_name": out_name,
        "mime_type": mime,
        "output_format": output_format,
    })

    return output_path, out_name, meta
