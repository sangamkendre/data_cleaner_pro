"""
Automated Unit Tests for PDF Converter and Excel/CSV Export Pipeline.
"""

import os
import unittest
import tempfile
import json
import pandas as pd
import numpy as np

from handlers import PDFHandler, get_handler_for_file
from conversion import (
    inspect_pdf_tables,
    extract_pdf_tables_to_df,
    convert_pdf_to_export_file,
    table_to_dataframe,
)
from app import app


class TestPDFConverter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_pdf = os.path.join("sample_data", "sample_sales_data.pdf")
        assert os.path.exists(cls.sample_pdf), f"Sample PDF not found at {cls.sample_pdf}"

    def test_handler_detection(self):
        handler = get_handler_for_file("sales_report.pdf")
        self.assertIsNotNone(handler)
        self.assertIsInstance(handler, PDFHandler)
        self.assertTrue(handler.can_handle("document.PDF"))
        self.assertFalse(handler.can_handle("document.xlsx"))

    def test_pdf_handler_sheets_and_read(self):
        handler = PDFHandler()
        sheets = handler.get_sheets(self.sample_pdf)
        self.assertIsInstance(sheets, list)
        self.assertGreater(len(sheets), 0)

        df, meta = handler.read(self.sample_pdf)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(meta["format"], "PDF")
        self.assertEqual(len(df), 12)
        self.assertIn("Order_ID", df.columns)
        self.assertIn("Total_Sales", df.columns)
        self.assertIn("Product", df.columns)

    def test_table_to_dataframe_cleaning(self):
        raw_table = [
            ["Order\nID", "Product Name  ", "Price", None, "Price"],
            ["101", "Laptop Pro", "50000", "Extra", "50000"],
            ["102", "Mouse\r\nOptical", "500", "", "500"],
        ]
        df = table_to_dataframe(raw_table)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.columns[0], "Order ID")
        self.assertEqual(df.columns[1], "Product Name")
        self.assertEqual(df.columns[2], "Price")
        self.assertEqual(df.columns[3], "Column_4")
        self.assertEqual(df.columns[4], "Price_1")  # Disambiguated duplicate
        self.assertEqual(df.iloc[1]["Product Name"], "Mouse Optical")

    def test_inspect_pdf_tables(self):
        info = inspect_pdf_tables(self.sample_pdf)
        self.assertTrue(info["has_extractable_data"])
        self.assertEqual(info["total_pages"], 1)
        self.assertEqual(info["total_tables"], 1)
        table0 = info["tables"][0]
        self.assertEqual(table0["rows"], 12)
        self.assertEqual(table0["columns"], 7)
        self.assertIn("Order_ID", table0["column_names"])
        self.assertGreater(len(table0["preview"]), 0)

    def test_convert_pdf_to_excel_and_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Excel conversion
            xlsx_out = os.path.join(tmpdir, "output.xlsx")
            export_path, name, meta = convert_pdf_to_export_file(
                self.sample_pdf,
                output_format="xlsx",
                output_path=xlsx_out,
            )
            self.assertTrue(os.path.exists(xlsx_out))
            self.assertEqual(meta["rows"], 12)
            # Verify Excel is readable by pandas
            df_excel = pd.read_excel(xlsx_out)
            self.assertEqual(len(df_excel), 12)
            self.assertIn("Order_ID", df_excel.columns)

            # CSV conversion
            csv_out = os.path.join(tmpdir, "output.csv")
            export_path_csv, name_csv, meta_csv = convert_pdf_to_export_file(
                self.sample_pdf,
                output_format="csv",
                output_path=csv_out,
            )
            self.assertTrue(os.path.exists(csv_out))
            df_csv = pd.read_csv(csv_out)
            self.assertEqual(len(df_csv), 12)
            self.assertIn("Total_Sales", df_csv.columns)


    def test_check_columns_match(self):
        from conversion import check_columns_match
        df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        df2 = pd.DataFrame({"A": [5, 6], "B": [7, 8]})
        df3 = pd.DataFrame({"X": [9, 10], "Y": [11, 12]})

        self.assertTrue(check_columns_match([("T1", df1), ("T2", df2)]))
        self.assertFalse(check_columns_match([("T1", df1), ("T3", df3)]))
        self.assertTrue(check_columns_match([("T1", df1)]))

    def test_sanitize_excel_sheet_name(self):
        from conversion import sanitize_excel_sheet_name
        seen = set()
        s1 = sanitize_excel_sheet_name("Sales [2026] / US:NY * Q1", 0, seen)
        self.assertNotIn("[", s1)
        self.assertNotIn("]", s1)
        self.assertNotIn(":", s1)
        self.assertNotIn("*", s1)
        self.assertNotIn("/", s1)
        self.assertLessEqual(len(s1), 31)

        # Disambiguate identical names
        s2 = sanitize_excel_sheet_name("Sales [2026] / US:NY * Q1", 1, seen)
        self.assertNotEqual(s1, s2)
        self.assertIn("_2", s2)

    def test_multi_schema_pdf_export_and_sheet_switching(self):
        sample_tables_pdf = r"c:\Users\HP\Downloads\sample-tables.pdf"
        if not os.path.exists(sample_tables_pdf):
            self.skipTest("sample-tables.pdf not found in Downloads")

        # 1. Inspect
        info = inspect_pdf_tables(sample_tables_pdf)
        self.assertFalse(info["columns_match"])
        self.assertGreater(info["total_tables"], 5)

        # 2. Extract default DataFrame - should default to Table 1, not sparse union
        df, meta = extract_pdf_tables_to_df(sample_tables_pdf)
        self.assertEqual(meta["selected_sheet"], info["tables"][0]["name"])
        self.assertEqual(len(df), info["tables"][0]["rows"])
        self.assertEqual(len(df.columns), info["tables"][0]["columns"])

        # 3. Export to Excel - should write multiple sheets for heterogeneous tables
        with tempfile.TemporaryDirectory() as tmpdir:
            out_xlsx = os.path.join(tmpdir, "multi_table.xlsx")
            export_path, name, export_meta = convert_pdf_to_export_file(
                sample_tables_pdf,
                output_format="xlsx",
                output_path=out_xlsx,
            )
            self.assertTrue(os.path.exists(out_xlsx))
            import openpyxl
            wb = openpyxl.load_workbook(out_xlsx)
            self.assertEqual(len(wb.sheetnames), info["total_tables"])
            # Verify first sheet has correct rows
            first_sheet_df = pd.read_excel(out_xlsx, sheet_name=wb.sheetnames[0])
            self.assertEqual(len(first_sheet_df), info["tables"][0]["rows"])
            wb.close()

            # 4. Export to CSV (all tables) - should generate a ZIP archive of CSVs
            out_csv = os.path.join(tmpdir, "multi_table.csv")
            export_path_csv, name_csv, meta_csv = convert_pdf_to_export_file(
                sample_tables_pdf,
                output_format="csv",
                output_path=out_csv,
            )
            self.assertTrue(name_csv.endswith(".zip"))
            import zipfile
            with zipfile.ZipFile(export_path_csv) as z:
                self.assertEqual(len(z.namelist()), info["total_tables"])


class TestFlaskPDFEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_pdf_inspect_demo_endpoint(self):
        res = self.client.post("/api/pdf/inspect", data={"demo": "true"})
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["data"]["total_pages"], 1)
        self.assertEqual(json_data["data"]["total_tables"], 1)

    def test_pdf_convert_demo_to_csv_endpoint(self):
        res = self.client.post("/api/pdf/convert", data={"demo": "true", "format": "csv"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        content = res.data.decode("utf-8")
        self.assertIn("Order_ID", content)
        self.assertIn("Laptop", content)

    def test_pdf_convert_demo_to_excel_endpoint(self):
        res = self.client.post("/api/pdf/convert", data={"demo": "true", "format": "xlsx"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.data) > 0)
        # Check Content-Type for openxml
        self.assertIn("spreadsheetml", res.headers.get("Content-Type", ""))

    def test_pdf_load_to_cleaner_endpoint(self):
        res = self.client.post("/api/pdf/load-to-cleaner", json={"is_demo": True})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("session_id", data)
        self.assertEqual(data["file_info"]["rows"], 12)
        self.assertEqual(data["file_info"]["file_type"], "PDF")

        # Test preview works with the newly created PDF session
        session_id = data["session_id"]
        preview_res = self.client.get(f"/api/preview?session_id={session_id}")
        self.assertEqual(preview_res.status_code, 200)
        prev_data = preview_res.get_json()
        self.assertEqual(prev_data["dataset_total_rows"], 12)

        # Test excel export endpoint works with this session
        export_excel_res = self.client.get(f"/api/export/excel?session_id={session_id}")
        self.assertEqual(export_excel_res.status_code, 200)
        self.assertIn("spreadsheetml", export_excel_res.headers.get("Content-Type", ""))

    def test_upload_demo_pdf_through_main_upload_endpoint(self):
        res = self.client.post("/api/upload", data={"demo": "true", "demo_type": "pdf"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["file_info"]["file_type"], "PDF")
        self.assertEqual(data["file_info"]["rows"], 12)

    def test_multi_table_pdf_in_cleaner_studio(self):
        sample_tables_pdf = r"c:\Users\HP\Downloads\sample-tables.pdf"
        if not os.path.exists(sample_tables_pdf):
            self.skipTest("sample-tables.pdf not found in Downloads")

        # Load PDF into cleaner via endpoint
        res = self.client.post(
            "/api/pdf/load-to-cleaner",
            json={"temp_path": sample_tables_pdf}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        session_id = data["session_id"]
        sheets = data["sheets"]
        self.assertGreater(len(sheets), 1)

        # Initial active sheet is Table 1
        self.assertEqual(data["selected_sheet"], sheets[0])

        # Switch to Table 2 via /api/select-sheet
        target_sheet = sheets[1]
        switch_res = self.client.post(
            "/api/select-sheet",
            json={"session_id": session_id, "sheet_name": target_sheet}
        )
        self.assertEqual(switch_res.status_code, 200)
        switch_data = switch_res.get_json()
        self.assertTrue(switch_data["success"])
        self.assertEqual(switch_data["selected_sheet"], target_sheet)

        # Verify preview on switched sheet
        prev_res = self.client.get(f"/api/preview?session_id={session_id}")
        self.assertEqual(prev_res.status_code, 200)
        prev_data = prev_res.get_json()
        self.assertGreater(prev_data["dataset_total_rows"], 0)


if __name__ == "__main__":
    unittest.main()
