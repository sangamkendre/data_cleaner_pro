"""
Automated Unit Tests for Multi-Sheet Excel Cleaning, State Persistence, and Workbook Export.
"""

import os
import unittest
import tempfile
import pandas as pd
from app import app
from session_manager import session_manager


class TestMultiSheetExcel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.excel_file = os.path.join("sample_data", "sample_ecommerce.xlsx")
        assert os.path.exists(cls.excel_file), f"Sample Excel not found at {cls.excel_file}"

    def setUp(self):
        self.client = app.test_client()

    def test_multisheet_upload_and_persistence(self):
        # 1. Ingest multi-sheet Excel
        res = self.client.post("/api/upload", data={"demo": "true", "demo_type": "excel"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        session_id = data["session_id"]
        sheets = data["sheets"]
        self.assertIn("Customers", sheets)
        self.assertIn("Orders", sheets)
        self.assertEqual(data["selected_sheet"], "Customers")

        # Check sheets overview returned
        overview = data.get("sheets_overview", [])
        self.assertGreater(len(overview), 0)
        cust_info = next(s for s in overview if s["name"] == "Customers")
        self.assertEqual(cust_info["rows"], 20)
        self.assertFalse(cust_info["is_cleaned"])

        # 2. Perform cleaning on "Customers" sheet (trim whitespace across text columns)
        clean_res = self.client.post("/api/clean/strings", json={
            "session_id": session_id,
            "trim_whitespace": True,
            "remove_extra_spaces": True,
            "empty_to_null": True,
        })
        self.assertEqual(clean_res.status_code, 200)

        # Verify Customers now has audit actions recorded
        summary_cust = self.client.get(f"/api/summary?session_id={session_id}").get_json()
        cust_actions = len(summary_cust.get("history", []))
        self.assertGreater(cust_actions, 0)

        # 3. Switch sheet to "Orders"
        select_orders = self.client.post("/api/select-sheet", json={
            "session_id": session_id,
            "sheet_name": "Orders"
        })
        self.assertEqual(select_orders.status_code, 200)
        orders_data = select_orders.get_json()
        self.assertEqual(orders_data["selected_sheet"], "Orders")
        self.assertEqual(orders_data["file_info"]["rows"], 6)

        # Preview orders
        prev_orders = self.client.get(f"/api/preview?session_id={session_id}").get_json()
        self.assertEqual(prev_orders["dataset_total_rows"], 6)
        self.assertIn("amount", prev_orders["columns"])

        # 4. Perform cleaning on "Orders" sheet (standardize date column)
        date_clean = self.client.post("/api/clean/date", json={
            "session_id": session_id,
            "column": "order_date",
            "output_format": "YYYY-MM-DD",
            "day_first": True,
        })
        self.assertEqual(date_clean.status_code, 200)
        summary_orders = self.client.get(f"/api/summary?session_id={session_id}").get_json()
        self.assertGreater(summary_orders["date_values_converted"], 0)

        # 5. Switch BACK to "Customers" sheet
        select_cust_again = self.client.post("/api/select-sheet", json={
            "session_id": session_id,
            "sheet_name": "Customers"
        })
        self.assertEqual(select_cust_again.status_code, 200)

        # Verify that Customers state was preserved with all previous cleanings!
        summary_cust_again = self.client.get(f"/api/summary?session_id={session_id}").get_json()
        self.assertEqual(len(summary_cust_again["history"]), cust_actions)

        # 6. Check sheets overview has updated statuses
        sheets_res = self.client.get(f"/api/sheets?session_id={session_id}").get_json()
        self.assertTrue(sheets_res["success"])
        overview = sheets_res["sheets_overview"]
        cust_stat = next(s for s in overview if s["name"] == "Customers")
        orders_stat = next(s for s in overview if s["name"] == "Orders")
        self.assertTrue(cust_stat["is_cleaned"])
        self.assertTrue(orders_stat["is_cleaned"])

        # 7. Test Workbook-level Excel Export
        export_res = self.client.get(f"/api/export/excel?session_id={session_id}")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("spreadsheetml", export_res.headers.get("Content-Type", ""))

        # Verify exported workbook has all sheets with pandas
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(export_res.data)
            tmp_path = tmp.name

        try:
            with pd.ExcelFile(tmp_path) as xl:
                self.assertIn("Customers", xl.sheet_names)
                self.assertIn("Orders", xl.sheet_names)
                df_cust = pd.read_excel(xl, "Customers")
                df_ord = pd.read_excel(xl, "Orders")
                self.assertEqual(len(df_cust), 20)
                self.assertEqual(len(df_ord), 6)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
