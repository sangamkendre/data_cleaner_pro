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


if __name__ == "__main__":
    unittest.main()
