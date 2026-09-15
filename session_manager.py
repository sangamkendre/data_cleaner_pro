"""
Session Manager.
Maintains session state, DataFrame versions, audit logs, and undo history.
"""

import os
import uuid
import time
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd


class DatasetSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.raw_df: Optional[pd.DataFrame] = None
        self.current_df: Optional[pd.DataFrame] = None
        self.file_info: Dict[str, Any] = {}
        self.active_sheet: Optional[str] = None
        self.sheets: List[str] = []
        self.original_file_path: Optional[str] = None

        # Audit counters
        self.audit = {
            "duplicate_rows_removed": 0,
            "null_values_handled": 0,
            "whitespace_issues_fixed": 0,
            "name_values_cleaned": 0,
            "contact_values_cleaned": 0,
            "email_values_cleaned": 0,
            "date_values_converted": 0,
            "data_types_fixed": 0,
            "rows_before": 0,
            "rows_after": 0,
            "actions_history": [],
        }

        # Undo stack (limited to last 10 states)
        self._history: List[Tuple[pd.DataFrame, Dict[str, Any], str]] = []

    def set_dataset(self, df: pd.DataFrame, file_info: Dict[str, Any], file_path: str = None):
        self.raw_df = df.copy()
        self.current_df = df.copy()
        self.file_info = file_info
        self.original_file_path = file_path
        self.sheets = file_info.get("sheets", [])
        self.active_sheet = file_info.get("selected_sheet")

        self.audit = {
            "duplicate_rows_removed": 0,
            "null_values_handled": 0,
            "whitespace_issues_fixed": 0,
            "name_values_cleaned": 0,
            "contact_values_cleaned": 0,
            "email_values_cleaned": 0,
            "date_values_converted": 0,
            "data_types_fixed": 0,
            "rows_before": len(df),
            "rows_after": len(df),
            "actions_history": [],
        }
        self._history = []

    def push_state(self, action_name: str):
        """Saves current state for undo capability."""
        if self.current_df is not None:
            # Keep maximum 8 previous states
            if len(self._history) >= 8:
                self._history.pop(0)
            self._history.append((self.current_df.copy(), dict(self.audit), action_name))

    def undo(self) -> Tuple[bool, str]:
        """Reverts to previous state."""
        if not self._history:
            return False, "No previous actions to undo."

        prev_df, prev_audit, action_name = self._history.pop()
        self.current_df = prev_df
        self.audit = prev_audit
        self.audit["rows_after"] = len(prev_df)
        return True, f"Undone: {action_name}"

    def reset_to_raw(self) -> Tuple[bool, str]:
        """Restores the dataset back to its original ingested state while preserving undo capability."""
        if self.raw_df is None:
            return False, "No dataset loaded to reset."

        self.push_state("Reset to Original Dataset")
        self.current_df = self.raw_df.copy()
        self.audit = {
            "duplicate_rows_removed": 0,
            "null_values_handled": 0,
            "whitespace_issues_fixed": 0,
            "name_values_cleaned": 0,
            "contact_values_cleaned": 0,
            "email_values_cleaned": 0,
            "date_values_converted": 0,
            "data_types_fixed": 0,
            "rows_before": len(self.raw_df),
            "rows_after": len(self.raw_df),
            "actions_history": [{
                "timestamp": time.strftime("%H:%M:%S"),
                "action": "Reset to original raw dataset",
                "count": 0,
                "rows_remaining": len(self.raw_df),
            }],
        }
        return True, "Dataset successfully reset to original state."

    def record_action(self, action_type: str, count: int, description: str):
        """Updates audit counters and logs history."""
        if action_type in self.audit:
            self.audit[action_type] += count

        if self.current_df is not None:
            self.audit["rows_after"] = len(self.current_df)

        self.audit["actions_history"].append({
            "timestamp": time.strftime("%H:%M:%S"),
            "action": description,
            "count": count,
            "rows_remaining": len(self.current_df) if self.current_df is not None else 0,
        })

    def get_preview(
        self,
        page: int = 1,
        page_size: int = 50,
        search_query: str = "",
        sort_col: str = None,
        sort_dir: str = "asc",
    ) -> Dict[str, Any]:
        """Returns paginated preview without overloading the browser."""
        if self.current_df is None or self.current_df.empty:
            return {
                "total_rows": 0,
                "total_pages": 0,
                "current_page": 1,
                "page_size": page_size,
                "columns": [],
                "rows": [],
            }

        df = self.current_df

        # Filter by search query across string columns if provided
        if search_query:
            query_lower = search_query.lower()
            mask = pd.Series(False, index=df.index)
            for col in df.columns:
                mask = mask | df[col].astype(str).str.lower().str.contains(query_lower, na=False)
            df = df[mask]

        # Sorting
        if sort_col and sort_col in df.columns:
            ascending = (sort_dir.lower() == "asc")
            try:
                df = df.sort_values(by=sort_col, ascending=ascending)
            except Exception:
                pass

        total_rows = len(df)
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_df = df.iloc[start_idx:end_idx]

        # Format rows for JSON serialization (handling NaNs, timestamps)
        rows = []
        for idx, row in page_df.iterrows():
            row_data = {"_row_index": int(idx)}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    row_data[col] = None
                elif hasattr(val, "isoformat"):
                    row_data[col] = val.isoformat()
                else:
                    row_data[col] = val
            rows.append(row_data)

        return {
            "total_rows": total_rows,
            "dataset_total_rows": len(self.current_df),
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "columns": list(self.current_df.columns),
            "column_types": {col: str(self.current_df[col].dtype) for col in self.current_df.columns},
            "rows": rows,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Returns before/after summary and audit stats."""
        return {
            "duplicate_rows_removed": self.audit["duplicate_rows_removed"],
            "null_values_handled": self.audit["null_values_handled"],
            "whitespace_issues_fixed": self.audit["whitespace_issues_fixed"],
            "name_values_cleaned": self.audit["name_values_cleaned"],
            "contact_values_cleaned": self.audit["contact_values_cleaned"],
            "email_values_cleaned": self.audit["email_values_cleaned"],
            "date_values_converted": self.audit["date_values_converted"],
            "data_types_fixed": self.audit["data_types_fixed"],
            "rows_before": self.audit["rows_before"],
            "rows_after": self.audit["rows_after"],
            "history": self.audit["actions_history"],
            "can_undo": len(self._history) > 0,
        }


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, DatasetSession] = {}

    def get_or_create_session(self, session_id: Optional[str] = None) -> DatasetSession:
        if not session_id or session_id not in self.sessions:
            new_id = session_id or str(uuid.uuid4())
            self.sessions[new_id] = DatasetSession(new_id)
            return self.sessions[new_id]
        return self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[DatasetSession]:
        return self.sessions.get(session_id)


# Global singleton
session_manager = SessionManager()
