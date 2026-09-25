"""
Smart Data Cleaning & Conversion Web App
Flask Application & API Routes
"""

import os
import uuid
import tempfile
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, make_response
from werkzeug.utils import secure_filename

from handlers import get_handler_for_file
from profiling import profile_dataset, get_file_info
from cleaning import (
    clean_string_column,
    clean_all_string_columns,
    replace_empty_with_null,
    clean_name_column,
    clean_contact_column,
    clean_email_column,
    clean_date_column,
    clean_null_values,
    remove_duplicates,
)
from conversion import (
    inspect_or_convert_type,
    preview_string_transformation,
    export_to_parquet,
    inspect_pdf_tables,
    extract_pdf_tables_to_df,
    convert_pdf_to_export_file,
)
from session_manager import session_manager


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

import math
import numpy as np
from flask.json.provider import DefaultJSONProvider

def sanitize_for_json(obj):
    """Recursively converts NaN, Infinity, -Infinity, and pd.NA into None for valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if obj is pd.NA:
        return None
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        val = obj.item()
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val
    if isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    return obj

class SafeJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return super().dumps(sanitize_for_json(obj), **kwargs)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.json = SafeJSONProvider(app)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024  # 250 MB max upload
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File is too large to process. Maximum upload size is 250 MB."}), 413


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": f"Internal server error: {str(error)}"}), 500


@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint or session resource not found."}), 404
    return error


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session = session_manager.get_or_create_session(session_id)

    is_demo = request.form.get("demo") == "true" or request.args.get("demo") == "true"
    demo_type = request.form.get("demo_type", "csv")

    if is_demo:
        if demo_type == "excel":
            file_path = os.path.join(SAMPLE_DIR, "sample_ecommerce.xlsx")
            filename = "sample_ecommerce.xlsx"
        elif demo_type == "sql":
            file_path = os.path.join(SAMPLE_DIR, "sample_database.sql")
            filename = "sample_database.sql"
        elif demo_type == "names":
            file_path = os.path.join(SAMPLE_DIR, "sample_names_messy.csv")
            filename = "last_names_sample.csv"
        elif demo_type == "pdf":
            file_path = os.path.join(SAMPLE_DIR, "sample_sales_data.pdf")
            filename = "sample_sales_data.pdf"
        else:
            file_path = os.path.join(SAMPLE_DIR, "sample_customers.csv")
            filename = "customer_data.csv"
    else:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, f"{session_id}_{filename}")
        file.save(file_path)

    handler = get_handler_for_file(filename)
    if not handler:
        return jsonify({"error": f"Unsupported file format for '{filename}'"}), 400

    try:
        df, meta = handler.read(file_path)
        file_info = get_file_info(df, file_path=file_path, filename=filename, file_type=meta.get("format", "Unknown"))
        file_info["sheets"] = meta.get("sheets", [])
        file_info["selected_sheet"] = meta.get("selected_sheet")

        session.set_dataset(df, file_info, file_path=file_path)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "file_info": file_info,
            "sheets": file_info.get("sheets", []),
            "selected_sheet": file_info.get("selected_sheet"),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500


@app.route("/api/select-sheet", methods=["POST"])
def select_sheet():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    sheet_name = data.get("sheet_name")

    session = session_manager.get_session(session_id)
    if not session or not session.original_file_path:
        return jsonify({"error": "Active session not found"}), 404

    handler = get_handler_for_file(session.file_info.get("file_name", ""))
    if not handler:
        return jsonify({"error": "Handler not found"}), 400

    try:
        df, meta = handler.read(session.original_file_path, sheet_name=sheet_name)
        file_info = get_file_info(df, file_path=session.original_file_path, filename=session.file_info.get("file_name"), file_type=meta.get("format"))
        file_info["sheets"] = session.sheets
        file_info["selected_sheet"] = sheet_name

        session.set_dataset(df, file_info, file_path=session.original_file_path)

        return jsonify({
            "success": True,
            "file_info": file_info,
            "selected_sheet": sheet_name,
        })
    except Exception as e:
        return jsonify({"error": f"Error loading sheet: {str(e)}"}), 500


@app.route("/api/preview", methods=["GET"])
def preview_data():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))
    search = request.args.get("search", "")
    sort_col = request.args.get("sort_col")
    sort_dir = request.args.get("sort_dir", "asc")

    preview = session.get_preview(page=page, page_size=page_size, search_query=search, sort_col=sort_col, sort_dir=sort_dir)
    return jsonify(preview)


@app.route("/api/profile", methods=["GET"])
def profile_data():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found or empty"}), 404

    report = profile_dataset(
        session.current_df,
        file_path=session.original_file_path,
        filename=session.file_info.get("file_name"),
        file_type=session.file_info.get("file_type", "Unknown"),
    )
    return jsonify(report)


@app.route("/api/duplicates", methods=["GET"])
def get_duplicates_info():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    report = profile_dataset(session.current_df)
    return jsonify(report["duplicate_analysis"])


@app.route("/api/clean/duplicates", methods=["POST"])
def clean_dups():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    subset = data.get("subset")
    keep = data.get("keep", "first")

    session.push_state("Remove Duplicates")
    df_cleaned, removed_count = remove_duplicates(session.current_df, subset=subset, keep=keep)
    session.current_df = df_cleaned
    session.record_action("duplicate_rows_removed", removed_count, f"Removed {removed_count} duplicate rows (keep={keep})")

    return jsonify({
        "success": True,
        "rows_removed": removed_count,
        "rows_remaining": len(df_cleaned),
    })


@app.route("/api/clean/nulls", methods=["POST"])
def clean_nulls():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    strategy = data.get("strategy", "replace")
    fill_value = data.get("fill_value", "Unknown")
    treat_empty = data.get("treat_empty_as_null", True)

    session.push_state(f"Handle Nulls in {column or 'all columns'}")
    df_cleaned, nulls_handled, rows_removed = clean_null_values(
        session.current_df,
        column=column,
        strategy=strategy,
        fill_value=fill_value,
        treat_empty_as_null=treat_empty,
    )
    session.current_df = df_cleaned

    action_desc = f"Handled {nulls_handled} nulls/empty cells in {column or 'all columns'} ({strategy})"
    if rows_removed > 0:
        action_desc += f", dropped {rows_removed} rows"
    session.record_action("null_values_handled", nulls_handled, action_desc)

    return jsonify({
        "success": True,
        "nulls_handled": nulls_handled,
        "rows_removed": rows_removed,
        "rows_remaining": len(df_cleaned),
    })


@app.route("/api/clean/empty-strings", methods=["POST"])
def clean_empty_strings():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    include_whitespace = data.get("include_whitespace", True)
    include_placeholders = data.get("include_placeholders", True)

    session.push_state(f"Convert Empty Strings to Null: {column or 'All Columns'}")
    df_cleaned, count = replace_empty_with_null(
        session.current_df,
        column=column,
        include_whitespace=include_whitespace,
        include_placeholders=include_placeholders,
    )
    session.current_df = df_cleaned
    session.record_action("null_values_handled", count, f"Converted {count} empty/blank strings to Null in {column or 'all columns'}")

    return jsonify({
        "success": True,
        "empty_strings_converted": count,
        "rows_remaining": len(df_cleaned),
    })


@app.route("/api/clean/strings", methods=["POST"])
def clean_strings():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    trim_ws = data.get("trim_whitespace", True)
    collapse_sp = data.get("remove_extra_spaces", True)
    case_tr = data.get("case_transform")
    strip_sp = data.get("remove_special_chars", False)
    empty_to_null = data.get("empty_to_null", True)

    session.push_state(f"Clean Strings: {column or 'All Columns'}")
    if column:
        df_cleaned, count = clean_string_column(
            session.current_df,
            column=column,
            trim_whitespace=trim_ws,
            remove_extra_spaces=collapse_sp,
            case_transform=case_tr,
            remove_special_chars=strip_sp,
            empty_to_null=empty_to_null,
        )
    else:
        df_cleaned, count = clean_all_string_columns(
            session.current_df,
            empty_to_null=empty_to_null,
            trim_whitespace=trim_ws,
            remove_extra_spaces=collapse_sp,
            case_transform=case_tr,
            remove_special_chars=strip_sp,
        )

    session.current_df = df_cleaned
    session.record_action("whitespace_issues_fixed", count, f"Cleaned text in {column or 'all columns'} ({count} cells updated)")

    return jsonify({"success": True, "modifications_count": count})


@app.route("/api/clean/names", methods=["POST"])
def clean_names():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    alphabets_only = data.get("alphabets_only", True)
    case_transform = data.get("case_transform", "title")
    allow_spaces = data.get("allow_spaces", True)

    session.push_state(f"Clean Names: {column or 'All Name Columns'}")
    df_cleaned, count = clean_name_column(
        session.current_df,
        column=column,
        alphabets_only=alphabets_only,
        case_transform=case_transform,
        allow_spaces=allow_spaces,
    )
    session.current_df = df_cleaned
    session.record_action(
        "name_values_cleaned",
        count,
        f"Sanitized names in '{column or 'all name columns'}' ({count} updated to alphabets only)",
    )

    return jsonify({
        "success": True,
        "cleaned_count": count,
    })


@app.route("/api/clean/contact", methods=["POST"])
def clean_contact():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    strip_non_digits = data.get("strip_non_digits", True)
    normalize_10 = data.get("normalize_10_digits", False)
    format_style = data.get("format_style", "digits_only")
    country_code = data.get("country_code", "91")

    session.push_state(f"Clean Contact: {column}")
    df_cleaned, cleaned_count, invalid_entries = clean_contact_column(
        session.current_df,
        column=column,
        strip_non_digits=strip_non_digits,
        normalize_10_digits=normalize_10,
        format_style=format_style,
        country_code=country_code,
    )
    session.current_df = df_cleaned
    session.record_action("contact_values_cleaned", cleaned_count, f"Cleaned contact numbers in '{column}' ({cleaned_count} updated)")

    return jsonify({
        "success": True,
        "cleaned_count": cleaned_count,
        "invalid_entries": invalid_entries,
    })


@app.route("/api/clean/email", methods=["POST"])
def clean_email():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    lowercase = data.get("lowercase", True)
    trim_spaces = data.get("trim_spaces", True)
    remove_inner = data.get("remove_inner_spaces", True)
    fix_typos = data.get("fix_domain_typos", True)

    session.push_state(f"Clean Email: {column}")
    df_cleaned, cleaned_count, invalid_entries = clean_email_column(
        session.current_df,
        column=column,
        lowercase=lowercase,
        trim_spaces=trim_spaces,
        remove_inner_spaces=remove_inner,
        fix_domain_typos=fix_typos,
    )
    session.current_df = df_cleaned
    session.record_action("email_values_cleaned", cleaned_count, f"Cleaned emails in '{column}' ({cleaned_count} updated)")

    return jsonify({
        "success": True,
        "cleaned_count": cleaned_count,
        "invalid_entries": invalid_entries,
    })


@app.route("/api/clean/date", methods=["POST"])
def clean_date():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    input_format = data.get("input_format") or None
    output_format = data.get("output_format", "YYYY-MM-DD")
    day_first = data.get("day_first", True)

    session.push_state(f"Standardize Dates in {column}")
    df_cleaned, count, unparseable = clean_date_column(
        session.current_df,
        column=column,
        input_format=input_format,
        output_format=output_format,
        day_first=day_first,
    )
    session.current_df = df_cleaned
    session.record_action("date_values_converted", count, f"Converted dates in '{column}' to {output_format} ({count} updated)")

    return jsonify({
        "success": True,
        "converted_count": count,
        "unparseable_records": unparseable,
    })


@app.route("/api/convert/type", methods=["POST"])
def convert_type():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found"}), 404

    column = data.get("column")
    target_type = data.get("target_type", "String")
    apply_fix = data.get("apply_fix", False)
    clean_currency = data.get("clean_currency_symbols", True)
    fill_unconvertible = data.get("fill_unconvertible")
    case_transform = data.get("case_transform")  # 'upper', 'lower', 'title', 'capitalize', None
    trim_whitespace = data.get("trim_whitespace", True)
    collapse_spaces = data.get("collapse_spaces", False)

    case_desc = f" ({case_transform.capitalize()} Case)" if (case_transform and target_type.lower() == "string") else ""
    if apply_fix:
        session.push_state(f"Convert {column} to {target_type}{case_desc}")

    df_result, problematic, converted = inspect_or_convert_type(
        session.current_df,
        column=column,
        target_type=target_type,
        apply_fix=apply_fix,
        clean_currency_symbols=clean_currency,
        fill_unconvertible=fill_unconvertible,
        case_transform=case_transform,
        trim_whitespace=trim_whitespace,
        collapse_spaces=collapse_spaces,
    )

    preview_samples = []
    if target_type.lower() == "string":
        preview_samples = preview_string_transformation(
            session.current_df,
            column=column,
            case_transform=case_transform,
            trim_whitespace=trim_whitespace,
            collapse_spaces=collapse_spaces,
            limit=10,
        )

    if apply_fix:
        session.current_df = df_result
        session.record_action(
            "data_types_fixed",
            1,
            f"Converted column '{column}' to {target_type}{case_desc} ({converted} values)"
        )

    return jsonify({
        "success": True,
        "applied": apply_fix,
        "converted_count": converted,
        "problematic_records": problematic,
        "total_problematic": len(problematic),
        "preview_samples": preview_samples,
    })


@app.route("/api/undo", methods=["POST"])
def undo_action():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    success, msg = session.undo()
    return jsonify({"success": success, "message": msg})


@app.route("/api/clean/auto", methods=["POST"])
def auto_clean_dataset():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "Session not found or dataset empty"}), 404

    clean_dups = data.get("clean_duplicates", True)
    clean_strs = data.get("clean_strings", True)
    clean_names = data.get("clean_names", True)
    clean_emails = data.get("clean_emails", True)
    clean_contacts = data.get("clean_contacts", True)
    clean_dates = data.get("clean_dates", True)
    clean_null = data.get("clean_nulls", True)
    convert_types = data.get("convert_types", True)

    session.push_state("1-Click Auto Clean All")
    report_before = profile_dataset(session.current_df)
    changes_summary = []

    # 1. Deduplication
    if clean_dups and report_before["duplicate_analysis"].get("has_duplicates"):
        df_cleaned, dup_count = remove_duplicates(session.current_df, keep="first")
        if dup_count > 0:
            session.current_df = df_cleaned
            session.record_action("duplicate_rows_removed", dup_count, f"Removed {dup_count} duplicate rows (keep=first)")
            changes_summary.append(f"Removed {dup_count} duplicate rows")

    # 2. Targeted column cleaning based on profiling
    for col_info in report_before.get("data_types", []):
        col = col_info["column"]
        if col not in session.current_df.columns:
            continue
        detected = col_info.get("detected_type")
        action = col_info.get("action")

        # Name Sanitization (alphabets only)
        if clean_names and (detected == "Name" or action == "Clean Names"):
            df_cleaned, count = clean_name_column(
                session.current_df,
                column=col,
                alphabets_only=True,
                case_transform="title",
            )
            if count > 0:
                session.current_df = df_cleaned
                session.record_action("name_values_cleaned", count, f"Sanitized names in '{col}' ({count} updated to alphabets only)")
                changes_summary.append(f"Sanitized names in '{col}' to alphabets only ({count} updated)")

        # Email Sanitization
        elif clean_emails and detected == "Email" and action == "Clean Email":
            df_cleaned, count, _ = clean_email_column(
                session.current_df,
                column=col,
                lowercase=True,
                trim_spaces=True,
                remove_inner_spaces=True,
                fix_domain_typos=True,
            )
            if count > 0:
                session.current_df = df_cleaned
                session.record_action("email_values_cleaned", count, f"Cleaned emails in '{col}' ({count} updated)")
                changes_summary.append(f"Cleaned {count} emails in '{col}'")

        # Phone / Contact Sanitization
        elif clean_contacts and detected == "Phone" and action == "Clean Contact":
            df_cleaned, count, _ = clean_contact_column(
                session.current_df,
                column=col,
                strip_non_digits=True,
                normalize_10_digits=True,
                country_code="91",
            )
            if count > 0:
                session.current_df = df_cleaned
                session.record_action("contact_values_cleaned", count, f"Cleaned phone numbers in '{col}' ({count} updated)")
                changes_summary.append(f"Normalized {count} phone numbers in '{col}'")

        # Date Standardization
        elif clean_dates and detected == "Date" and action == "Fix Date":
            df_cleaned, count, _ = clean_date_column(
                session.current_df,
                column=col,
                output_format="YYYY-MM-DD",
                day_first=True,
            )
            if count > 0:
                session.current_df = df_cleaned
                session.record_action("date_values_converted", count, f"Standardized dates in '{col}' to YYYY-MM-DD ({count} updated)")
                changes_summary.append(f"Standardized {count} dates in '{col}'")

        # Type conversion (currency / numeric strings)
        elif convert_types and action and "Convert to" in action:
            target = action.replace("Convert to", "").strip()
            df_res, prob, conv = inspect_or_convert_type(
                session.current_df,
                column=col,
                target_type=target,
                apply_fix=True,
                clean_currency_symbols=True,
            )
            if conv > 0:
                session.current_df = df_res
                session.record_action("data_types_fixed", 1, f"Converted column '{col}' to {target} ({conv} values)")
                changes_summary.append(f"Converted column '{col}' to {target} ({conv} values)")

    # 3. General Whitespace & Empty String Cleaning on Text Columns
    if clean_strs:
        df_cleaned, count = clean_all_string_columns(session.current_df, empty_to_null=True)
        if count > 0:
            session.current_df = df_cleaned
            session.record_action("whitespace_issues_fixed", count, f"Cleaned whitespace & empty strings across text columns ({count} cells updated)")
            changes_summary.append(f"Cleaned whitespace & converted empty strings ({count} cells updated)")

    # 4. Null Value Handling (safe imputation)
    if clean_null:
        total_null_handled = 0
        for col in session.current_df.columns:
            null_count = int(session.current_df[col].isna().sum())
            if null_count > 0:
                is_num = pd.api.types.is_numeric_dtype(session.current_df[col])
                strat = "median" if is_num else "replace"
                fval = "Unknown" if not is_num else None
                df_cleaned, handled, _ = clean_null_values(
                    session.current_df,
                    column=col,
                    strategy=strat,
                    fill_value=fval,
                )
                session.current_df = df_cleaned
                total_null_handled += handled
        if total_null_handled > 0:
            session.record_action("null_values_handled", total_null_handled, f"Handled {total_null_handled} null values with safe imputation")
            changes_summary.append(f"Imputed/filled {total_null_handled} null values")

    report_after = profile_dataset(session.current_df)
    return jsonify({
        "success": True,
        "changes": changes_summary,
        "new_report": report_after,
        "quality_before": report_before.get("quality", {}),
        "quality_after": report_after.get("quality", {}),
    })


@app.route("/api/reset", methods=["POST"])
def reset_dataset():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    success, msg = session.reset_to_raw()
    return jsonify({"success": success, "message": msg})


@app.route("/api/summary", methods=["GET"])
def get_summary():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(session.get_summary())


@app.route("/api/export/parquet", methods=["GET"])
def export_parquet():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "No active dataset to export"}), 404

    base_name = os.path.splitext(session.file_info.get("file_name", "cleaned_dataset"))[0]
    out_name = f"{base_name}_cleaned.parquet"
    out_path = os.path.join(EXPORT_DIR, f"{session_id}_{out_name}")

    export_path, meta = export_to_parquet(session.current_df, out_path)
    return send_file(export_path, as_attachment=True, download_name=out_name, mimetype="application/octet-stream")


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "No active dataset to export"}), 404

    base_name = os.path.splitext(session.file_info.get("file_name", "cleaned_dataset"))[0]
    out_name = f"{base_name}_cleaned.csv"
    out_path = os.path.join(EXPORT_DIR, f"{session_id}_{out_name}")

    session.current_df.to_csv(out_path, index=False)
    return send_file(out_path, as_attachment=True, download_name=out_name, mimetype="text/csv")


@app.route("/api/export/excel", methods=["GET"])
def export_excel():
    session_id = request.args.get("session_id")
    session = session_manager.get_session(session_id)
    if not session or session.current_df is None:
        return jsonify({"error": "No active dataset to export"}), 404

    base_name = os.path.splitext(session.file_info.get("file_name", "cleaned_dataset"))[0]
    out_name = f"{base_name}_cleaned.xlsx"
    out_path = os.path.join(EXPORT_DIR, f"{session_id}_{out_name}")

    session.current_df.to_excel(out_path, index=False, engine="openpyxl")
    return send_file(
        out_path,
        as_attachment=True,
        download_name=out_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/api/pdf/inspect", methods=["POST"])
def inspect_pdf_endpoint():
    is_demo = request.form.get("demo") == "true" or request.args.get("demo") == "true"
    if is_demo:
        file_path = os.path.join(SAMPLE_DIR, "sample_sales_data.pdf")
        filename = "sample_sales_data.pdf"
    else:
        if "file" not in request.files:
            return jsonify({"error": "No PDF file uploaded"}), 400
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "Empty filename"}), 400
        temp_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, f"inspect_{temp_id}_{filename}")
        file.save(file_path)

    try:
        info = inspect_pdf_tables(file_path)
        return jsonify({
            "success": True,
            "data": info,
            "filename": filename,
            "temp_path": file_path if not is_demo else None,
            "is_demo": is_demo
        })
    except Exception as e:
        return jsonify({"error": f"Failed to inspect PDF: {str(e)}"}), 500


@app.route("/api/pdf/convert", methods=["POST"])
def convert_pdf_endpoint():
    is_demo = request.form.get("demo") == "true" or request.args.get("demo") == "true"
    fmt = request.form.get("format", "xlsx").lower().strip()
    selection = request.form.get("selection")
    temp_path = request.form.get("temp_path")

    if is_demo:
        file_path = os.path.join(SAMPLE_DIR, "sample_sales_data.pdf")
    elif temp_path and os.path.exists(temp_path):
        file_path = temp_path
    elif "file" in request.files:
        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No file uploaded"}), 400
        temp_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, f"conv_{temp_id}_{filename}")
        file.save(file_path)
    else:
        return jsonify({"error": "No PDF source provided"}), 400

    try:
        out_id = str(uuid.uuid4())
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ext = ".xlsx" if fmt in ("xlsx", "excel") else ".csv"
        out_filename = f"{base_name}_converted{ext}"
        out_path = os.path.join(EXPORT_DIR, f"{out_id}_{out_filename}")

        export_path, download_name, meta = convert_pdf_to_export_file(
            file_path,
            output_format=fmt,
            table_selection=selection,
            output_path=out_path
        )
        return send_file(
            export_path,
            as_attachment=True,
            download_name=download_name,
            mimetype=meta.get("mime_type", "application/octet-stream")
        )
    except Exception as e:
        return jsonify({"error": f"PDF conversion failed: {str(e)}"}), 500


@app.route("/api/pdf/load-to-cleaner", methods=["POST"])
def load_pdf_to_cleaner_endpoint():
    data = request.get_json() or {}
    temp_path = data.get("temp_path")
    is_demo = data.get("is_demo", False)
    selection = data.get("selection")

    if is_demo:
        file_path = os.path.join(SAMPLE_DIR, "sample_sales_data.pdf")
        filename = "sample_sales_data.pdf"
    elif temp_path and os.path.exists(temp_path):
        file_path = temp_path
        filename = os.path.basename(file_path).split("_", 2)[-1]
    else:
        return jsonify({"error": "PDF file reference not found or expired"}), 400

    session_id = str(uuid.uuid4())
    session = session_manager.get_or_create_session(session_id)

    try:
        df, meta = extract_pdf_tables_to_df(file_path, table_selection=selection)
        file_info = get_file_info(df, file_path=file_path, filename=filename, file_type="PDF")
        file_info["sheets"] = meta.get("sheets", [])
        file_info["selected_sheet"] = meta.get("selected_sheet")

        session.set_dataset(df, file_info, file_path=file_path)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "file_info": file_info,
            "sheets": file_info.get("sheets", []),
            "selected_sheet": file_info.get("selected_sheet"),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load PDF into cleaner: {str(e)}"}), 500


if __name__ == "__main__":
    print("Starting Smart Data Cleaner Web App on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
