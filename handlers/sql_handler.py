"""
SQL File Handler.
Parses .sql dump files (MySQL, PostgreSQL, SQLite) containing CREATE TABLE and INSERT INTO statements.
"""

import os
import re
import sqlite3
from typing import Dict, Any, Tuple, List
import pandas as pd
from handlers.base_handler import BaseHandler


class SQLHandler(BaseHandler):
    EXTENSIONS = {".sql"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def _extract_tables_regex(self, sql_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Regex-based extractor for INSERT INTO `table` (cols) VALUES (...), (...)
        Works across MySQL, PostgreSQL, SQLite syntax.
        """
        tables_data: Dict[str, List[Dict[str, Any]]] = {}

        # Match INSERT INTO `?table`? [(col1, col2, ...)] VALUES ...
        insert_pattern = re.compile(
            r"INSERT\s+INTO\s+[`\"']?([a-zA-Z0-9_]+)[`\"']?\s*(?:\(([^)]+)\))?\s+VALUES\s*(.+?);",
            re.IGNORECASE | re.DOTALL,
        )

        for match in insert_pattern.finditer(sql_content):
            table_name = match.group(1)
            columns_str = match.group(2)
            values_block = match.group(3)

            columns = []
            if columns_str:
                columns = [c.strip().strip("`\"'") for c in columns_str.split(",")]

            # Parse tuple values like (1, 'val', NULL), (2, 'val2', 3.5)
            row_pattern = re.compile(r"\((.*?)\)(?:,\s*\(|\s*$)", re.DOTALL)
            parsed_rows = []
            for row_match in row_pattern.finditer(values_block):
                row_raw = row_match.group(1)
                # Split elements respecting quotes
                items = re.findall(r"(?:'[^']*'|\"[^\"]*\"|[^,]+)", row_raw)
                clean_items = []
                for item in items:
                    val = item.strip()
                    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                        clean_items.append(val[1:-1])
                    elif val.upper() == "NULL":
                        clean_items.append(None)
                    else:
                        try:
                            if "." in val:
                                clean_items.append(float(val))
                            else:
                                clean_items.append(int(val))
                        except ValueError:
                            clean_items.append(val)
                parsed_rows.append(clean_items)

            if parsed_rows:
                if not columns:
                    columns = [f"column_{i+1}" for i in range(len(parsed_rows[0]))]

                if table_name not in tables_data:
                    tables_data[table_name] = []

                for row in parsed_rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i] if i < len(row) else None
                    tables_data[table_name].append(row_dict)

        return tables_data

    def get_sheets(self, file_path: str) -> List[str]:
        """Returns list of discovered tables from SQL file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tables = self._extract_tables_regex(content)
            if tables:
                return list(tables.keys())

            # Fallback: scan for CREATE TABLE table_name
            create_tables = re.findall(r"CREATE\s+TABLE\s+[`\"']?([a-zA-Z0-9_]+)[`\"']?", content, re.IGNORECASE)
            return list(set(create_tables))
        except Exception:
            return []

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        tables_data = self._extract_tables_regex(content)
        selected_table = kwargs.get("sheet_name") or kwargs.get("table_name")

        if tables_data:
            if not selected_table or selected_table not in tables_data:
                selected_table = list(tables_data.keys())[0]

            df = pd.DataFrame(tables_data[selected_table])
            metadata = {
                "format": "SQL",
                "sheets": list(tables_data.keys()),
                "selected_sheet": selected_table,
                "rows": len(df),
                "columns": len(df.columns),
            }
            return df, metadata

        # Fallback: try sqlite in-memory script execution
        try:
            conn = sqlite3.connect(":memory:")
            conn.executescript(content)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]
            if tables:
                target_table = selected_table if selected_table in tables else tables[0]
                df = pd.read_sql_query(f"SELECT * FROM `{target_table}`", conn)
                conn.close()
                return df, {
                    "format": "SQL",
                    "sheets": tables,
                    "selected_sheet": target_table,
                    "rows": len(df),
                    "columns": len(df.columns),
                }
        except Exception:
            pass

        # If empty
        return pd.DataFrame(), {
            "format": "SQL",
            "sheets": [],
            "selected_sheet": "",
            "rows": 0,
            "columns": 0,
        }
