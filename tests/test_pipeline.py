"""
Automated Unit Tests for Smart Data Cleaning & Conversion Pipeline.
"""

import os
import unittest
import tempfile
import pandas as pd
import numpy as np

from handlers import CSVHandler, ExcelHandler, ParquetHandler, SQLHandler, get_handler_for_file
from profiling import profile_dataset, get_file_info, detect_column_types, analyze_duplicates, analyze_nulls
from cleaning import (
    clean_string_column,
    clean_all_string_columns,
    clean_name_column,
    clean_contact_column,
    clean_email_column,
    clean_date_column,
    clean_null_values,
    remove_duplicates,
)
from conversion import inspect_or_convert_type, preview_string_transformation, export_to_parquet



class TestDataCleanerPipeline(unittest.TestCase):
    def setUp(self):
        self.sample_csv = "sample_data/sample_customers.csv"
        self.sample_excel = "sample_data/sample_ecommerce.xlsx"
        self.sample_sql = "sample_data/sample_database.sql"

    def test_handlers_detection(self):
        self.assertIsInstance(get_handler_for_file("data.csv"), CSVHandler)
        self.assertIsInstance(get_handler_for_file("data.xlsx"), ExcelHandler)
        self.assertIsInstance(get_handler_for_file("data.parquet"), ParquetHandler)
        self.assertIsInstance(get_handler_for_file("data.sql"), SQLHandler)

    def test_csv_handler_read(self):
        handler = CSVHandler()
        df, meta = handler.read(self.sample_csv)
        self.assertGreater(len(df), 0)
        self.assertEqual(meta["format"], "CSV")
        self.assertIn("name", df.columns)

    def test_excel_handler_read_and_sheets(self):
        handler = ExcelHandler()
        sheets = handler.get_sheets(self.sample_excel)
        self.assertIn("Customers", sheets)
        self.assertIn("Orders", sheets)
        df, meta = handler.read(self.sample_excel, sheet_name="Orders")
        self.assertIn("amount", df.columns)

    def test_sql_handler_read(self):
        handler = SQLHandler()
        df, meta = handler.read(self.sample_sql)
        self.assertGreater(len(df), 0)
        self.assertEqual(meta["format"], "SQL")

    def test_profiling_engine(self):
        df = pd.read_csv(self.sample_csv)
        report = profile_dataset(df, file_path=self.sample_csv, filename="sample.csv", file_type="CSV")
        self.assertIn("quality", report)
        self.assertIn("data_types", report)
        self.assertIn("null_analysis", report)
        self.assertIn("duplicate_analysis", report)
        self.assertTrue(report["duplicate_analysis"]["has_duplicates"])
        self.assertGreater(report["null_analysis"]["total_nulls"], 0)

    def test_contact_cleaner(self):
        df = pd.DataFrame({"phone": ["+91-98765-43210", "98abc7654321", "98765 43210"]})
        cleaned_df, count, invalid = clean_contact_column(df, "phone", strip_non_digits=True)
        self.assertEqual(cleaned_df["phone"].iloc[0], "919876543210")
        self.assertEqual(cleaned_df["phone"].iloc[1], "987654321")
        self.assertEqual(cleaned_df["phone"].iloc[2], "9876543210")
        self.assertEqual(count, 3)

    def test_email_cleaner(self):
        df = pd.DataFrame({"email": [" rahul.sharma@gmai.com ", "AMIT@YAHOOO.COM", "invalid-mail"]})
        cleaned_df, count, invalid = clean_email_column(df, "email", lowercase=True, trim_spaces=True, fix_domain_typos=True)
        self.assertEqual(cleaned_df["email"].iloc[0], "rahul.sharma@gmail.com")
        self.assertEqual(cleaned_df["email"].iloc[1], "amit@yahoo.com")
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0]["original"], "invalid-mail")

    def test_date_cleaner(self):
        df = pd.DataFrame({"date_col": ["12/05/2026", "2026-05-12", "12-05-2026"]})
        cleaned_df, count, unparseable = clean_date_column(df, "date_col", output_format="YYYY-MM-DD")
        self.assertEqual(cleaned_df["date_col"].iloc[1], "2026-05-12")
        self.assertEqual(len(unparseable), 0)

    def test_string_cleaner(self):
        df = pd.DataFrame({"city": ["  Mumbai  ", "   Pune   ", "delhi"]})
        cleaned_df, count = clean_string_column(df, "city", trim_whitespace=True, case_transform="title")
        self.assertEqual(cleaned_df["city"].iloc[0], "Mumbai")
        self.assertEqual(cleaned_df["city"].iloc[1], "Pune")
        self.assertEqual(cleaned_df["city"].iloc[2], "Delhi")

    def test_null_cleaner(self):
        df = pd.DataFrame({"val": [10.0, np.nan, 30.0]})
        cleaned_df, handled, dropped = clean_null_values(df, "val", strategy="mean")
        self.assertEqual(cleaned_df["val"].iloc[1], 20.0)
        self.assertEqual(handled, 1)

    def test_duplicate_cleaner(self):
        df = pd.DataFrame({"id": [1, 1, 2], "name": ["A", "A", "B"]})
        cleaned_df, removed = remove_duplicates(df)
        self.assertEqual(len(cleaned_df), 2)
        self.assertEqual(removed, 1)

    def test_type_converter_issue_reporting(self):
        df = pd.DataFrame({"salary": ["₹50,000", "75000", "unknown"]})
        # Inspect without applying fix
        _, problematic, _ = inspect_or_convert_type(df, "salary", "Float", apply_fix=False)
        self.assertEqual(len(problematic), 1)
        self.assertEqual(problematic[0]["original_value"], "unknown")

        # Now apply fix with currency cleaning
        df_conv, _, converted = inspect_or_convert_type(df, "salary", "Float", apply_fix=True)
        self.assertEqual(df_conv["salary"].iloc[0], 50000.0)
        self.assertEqual(df_conv["salary"].iloc[1], 75000.0)
        self.assertTrue(pd.isna(df_conv["salary"].iloc[2]))

    def test_type_converter_string_casing(self):
        df = pd.DataFrame({"city": ["  mumbai  ", "new   delhi", "BANGALORE", np.nan]})

        # Test Title Case
        df_title, _, count = inspect_or_convert_type(df, "city", "String", apply_fix=True, case_transform="title", trim_whitespace=True, collapse_spaces=True)
        self.assertEqual(df_title["city"].iloc[0], "Mumbai")
        self.assertEqual(df_title["city"].iloc[1], "New Delhi")
        self.assertEqual(df_title["city"].iloc[2], "Bangalore")
        self.assertTrue(pd.isna(df_title["city"].iloc[3]))
        self.assertEqual(count, 3)

        # Test Uppercase
        df_upper, _, _ = inspect_or_convert_type(df, "city", "String", apply_fix=True, case_transform="upper", trim_whitespace=True)
        self.assertEqual(df_upper["city"].iloc[0], "MUMBAI")
        self.assertEqual(df_upper["city"].iloc[1], "NEW   DELHI")

        # Test Lowercase
        df_lower, _, _ = inspect_or_convert_type(df, "city", "String", apply_fix=True, case_transform="lower", trim_whitespace=True)
        self.assertEqual(df_lower["city"].iloc[0], "mumbai")
        self.assertEqual(df_lower["city"].iloc[2], "bangalore")

    def test_type_converter_string_preview(self):
        df = pd.DataFrame({"name": [" rahul  sharma ", "priya singh"]})
        previews = preview_string_transformation(df, "name", case_transform="title", trim_whitespace=True, collapse_spaces=True)
        self.assertEqual(len(previews), 2)
        self.assertEqual(previews[0]["original_value"], " rahul  sharma ")
        self.assertEqual(previews[0]["transformed_value"], "Rahul Sharma")
        self.assertTrue(previews[0]["changed"])

    def test_clean_all_string_columns_casing(self):
        df = pd.DataFrame({
            "col1": ["  apple ", "banana"],
            "col2": ["cat", " dog "],
            "num": [1, 2],
        })
        cleaned_df, count = clean_all_string_columns(df, trim_whitespace=True, case_transform="upper")
        self.assertEqual(cleaned_df["col1"].iloc[0], "APPLE")
        self.assertEqual(cleaned_df["col1"].iloc[1], "BANANA")
        self.assertEqual(cleaned_df["col2"].iloc[0], "CAT")
        self.assertEqual(cleaned_df["col2"].iloc[1], "DOG")
        self.assertEqual(cleaned_df["num"].iloc[0], 1)

    def test_parquet_export(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            out_path, meta = export_to_parquet(df, tmp_path)
            self.assertTrue(os.path.exists(out_path))
            self.assertEqual(meta["format"], "Parquet")
            read_back = pd.read_parquet(out_path)
            self.assertEqual(len(read_back), 2)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_parquet_handler_read(self):
        df = pd.DataFrame({"id": [10, 20, 30], "item": ["apple", "banana", "cherry"]})
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            df.to_parquet(tmp_path)
            handler = ParquetHandler()
            self.assertTrue(handler.can_handle("data.parquet"))
            self.assertTrue(handler.can_handle("data.pq"))
            read_df, meta = handler.read(tmp_path)
            self.assertEqual(meta["format"], "Parquet")
            self.assertEqual(meta["rows"], 3)
            self.assertEqual(meta["columns"], 2)
            self.assertEqual(list(read_df["item"]), ["apple", "banana", "cherry"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_session_reset_to_raw(self):
        from session_manager import DatasetSession
        session = DatasetSession("test_reset")
        raw_df = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
        session.set_dataset(raw_df, {"file_name": "test.csv"})

        # Modify current_df
        session.current_df = pd.DataFrame({"id": [1], "val": ["A"]})
        self.assertEqual(len(session.current_df), 1)

        # Reset to raw
        success, msg = session.reset_to_raw()
        self.assertTrue(success)
        self.assertEqual(len(session.current_df), 2)

    def test_auto_clean_and_reset_endpoints(self):
        from app import app
        client = app.test_client()

        # Load demo CSV
        res = client.post("/api/upload", data={"demo": "true", "demo_type": "csv"})
        data = res.get_json()
        self.assertTrue(data["success"])
        session_id = data["session_id"]

        # Run 1-click Auto Clean
        clean_res = client.post("/api/clean/auto", json={"session_id": session_id})
        clean_data = clean_res.get_json()
        self.assertTrue(clean_data["success"])
        self.assertGreater(len(clean_data["changes"]), 0)
        self.assertGreaterEqual(clean_data["quality_after"]["score"], clean_data["quality_before"]["score"])

        # Run Reset
        reset_res = client.post("/api/reset", json={"session_id": session_id})
        reset_data = reset_res.get_json()
        self.assertTrue(reset_data["success"])

    def test_name_cleaner_removes_special_chars(self):
        # Using the exact examples from the user's spreadsheet image
        df = pd.DataFrame({
            "Last_Name": [
                "Baggins",
                "Nadir",
                "/White",
                "Schrute",
                "...Potter",
                "Flenderson_",
                "Mary_Jane",
                "007Bond",
                np.nan,
            ]
        })
        cleaned_df, count = clean_name_column(df, "Last_Name", alphabets_only=True, case_transform="title")
        self.assertEqual(cleaned_df["Last_Name"].iloc[0], "Baggins")
        self.assertEqual(cleaned_df["Last_Name"].iloc[1], "Nadir")
        self.assertEqual(cleaned_df["Last_Name"].iloc[2], "White")      # /White -> White
        self.assertEqual(cleaned_df["Last_Name"].iloc[3], "Schrute")
        self.assertEqual(cleaned_df["Last_Name"].iloc[4], "Potter")     # ...Potter -> Potter
        self.assertEqual(cleaned_df["Last_Name"].iloc[5], "Flenderson") # Flenderson_ -> Flenderson
        self.assertEqual(cleaned_df["Last_Name"].iloc[6], "Mary Jane")  # Mary_Jane -> Mary Jane
        self.assertEqual(cleaned_df["Last_Name"].iloc[7], "Bond")       # 007Bond -> Bond
        self.assertTrue(pd.isna(cleaned_df["Last_Name"].iloc[8]))       # NaN remains NaN
        self.assertEqual(count, 5)

    def test_name_profiler_detection(self):
        df = pd.DataFrame({
            "Last_Name": ["Baggins", "/White", "...Potter", "Flenderson_"]
        })
        types = detect_column_types(df)
        col_type = next(c for c in types if c["column"] == "Last_Name")
        self.assertEqual(col_type["detected_type"], "Name")
        self.assertEqual(col_type["status"], "⚠")
        self.assertEqual(col_type["action"], "Clean Names")

    def test_clean_names_endpoint(self):
        from app import app
        client = app.test_client()

        # Upload demo CSV
        res = client.post("/api/upload", data={"demo": "true", "demo_type": "csv"})
        data = res.get_json()
        session_id = data["session_id"]

        # Call /api/clean/names
        clean_res = client.post("/api/clean/names", json={
            "session_id": session_id,
            "column": "name",
            "alphabets_only": True,
            "case_transform": "title",
        })
        clean_data = clean_res.get_json()
        self.assertTrue(clean_data["success"])
        self.assertIn("cleaned_count", clean_data)

    def test_replace_empty_with_null(self):
        from cleaning import replace_empty_with_null
        df = pd.DataFrame({
            "colA": ["Alice", "", "   ", "Bob", "N/A", "null"],
            "colB": [1, 2, 3, 4, 5, 6]
        })
        cleaned_df, count = replace_empty_with_null(df, "colA", include_whitespace=True, include_placeholders=True)
        self.assertEqual(count, 4)  # "", "   ", "N/A", "null"
        self.assertTrue(pd.isna(cleaned_df["colA"].iloc[1]))
        self.assertTrue(pd.isna(cleaned_df["colA"].iloc[2]))
        self.assertTrue(pd.isna(cleaned_df["colA"].iloc[4]))
        self.assertTrue(pd.isna(cleaned_df["colA"].iloc[5]))
        self.assertEqual(cleaned_df["colA"].iloc[0], "Alice")
        self.assertEqual(cleaned_df["colA"].iloc[3], "Bob")

    def test_null_analysis_empty_string_detection(self):
        from profiling.null_analysis import analyze_nulls
        df = pd.DataFrame({
            "city": ["Mumbai", "", "   ", "Delhi", None]
        })
        res = analyze_nulls(df)
        self.assertEqual(res["total_nulls"], 3)  # 1 NaN + 2 empty/whitespace
        self.assertEqual(res["total_empty_strings"], 2)
        col_res = res["columns"][0]
        self.assertEqual(col_res["na_count"], 1)
        self.assertEqual(col_res["empty_string_count"], 2)
        self.assertEqual(col_res["null_count"], 3)

    def test_clean_null_values_with_empty_strings(self):
        from cleaning import clean_null_values
        df = pd.DataFrame({
            "city": ["Mumbai", "", "Delhi", None]
        })
        # replace strategy
        cleaned_df, handled, dropped = clean_null_values(df, "city", strategy="replace", fill_value="Unknown", treat_empty_as_null=True)
        self.assertEqual(handled, 2)
        self.assertEqual(cleaned_df["city"].iloc[1], "Unknown")
        self.assertEqual(cleaned_df["city"].iloc[3], "Unknown")

        # drop strategy
        df2 = pd.DataFrame({
            "city": ["Mumbai", "", "Delhi", None]
        })
        cleaned_df2, handled2, dropped2 = clean_null_values(df2, "city", strategy="remove_rows", treat_empty_as_null=True)
        self.assertEqual(dropped2, 2)
        self.assertEqual(len(cleaned_df2), 2)

    def test_clean_empty_strings_endpoint(self):
        from app import app
        client = app.test_client()

        res = client.post("/api/upload", data={"demo": "true", "demo_type": "csv"})
        data = res.get_json()
        session_id = data["session_id"]

        clean_res = client.post("/api/clean/empty-strings", json={
            "session_id": session_id,
            "column": None,
            "include_whitespace": True,
            "include_placeholders": True,
        })
    def test_convert_type_string_casing_endpoint(self):
        from app import app
        client = app.test_client()

        res = client.post("/api/upload", data={"demo": "true", "demo_type": "csv"})
        data = res.get_json()
        session_id = data["session_id"]

        # Inspect mode
        inspect_res = client.post("/api/convert/type", json={
            "session_id": session_id,
            "column": "city",
            "target_type": "String",
            "case_transform": "upper",
            "apply_fix": False,
        })
        inspect_data = inspect_res.get_json()
        self.assertTrue(inspect_data["success"])
        self.assertFalse(inspect_data["applied"])
        self.assertIn("preview_samples", inspect_data)
        self.assertGreater(len(inspect_data["preview_samples"]), 0)
        self.assertTrue(any(p["transformed_value"].isupper() for p in inspect_data["preview_samples"]))

        # Apply mode
        apply_res = client.post("/api/convert/type", json={
            "session_id": session_id,
            "column": "city",
            "target_type": "String",
            "case_transform": "upper",
            "apply_fix": True,
        })
        apply_data = apply_res.get_json()
        self.assertTrue(apply_data["success"])
        self.assertTrue(apply_data["applied"])

        # Check preview
        prev_res = client.get(f"/api/preview?session_id={session_id}&page=1&page_size=5")
        prev_data = prev_res.get_json()
        for row in prev_data["rows"]:
            if row.get("city"):
                self.assertEqual(row["city"], row["city"].upper())

        # Test Undo
        undo_res = client.post("/api/undo", json={"session_id": session_id})
        undo_data = undo_res.get_json()
        self.assertTrue(undo_data["success"])


if __name__ == "__main__":
    unittest.main()


