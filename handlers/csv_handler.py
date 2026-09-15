"""
CSV File Handler.
Supports .csv, .tsv, .txt with automatic delimiter sniffing and encoding detection.
"""

import os
import csv
from typing import Dict, Any, Tuple
import pandas as pd
from handlers.base_handler import BaseHandler


class CSVHandler(BaseHandler):
    EXTENSIONS = {".csv", ".tsv", ".txt"}

    def can_handle(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.EXTENSIONS

    def _detect_delimiter_and_encoding(self, file_path: str) -> Tuple[str, str]:
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        sample_bytes = b""
        detected_enc = "utf-8"

        for enc in encodings:
            try:
                with open(file_path, "rb") as f:
                    sample_bytes = f.read(8192)
                sample_bytes.decode(enc)
                detected_enc = enc
                break
            except (UnicodeDecodeError, Exception):
                continue

        text_sample = sample_bytes.decode(detected_enc, errors="ignore")
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(text_sample, delimiters=[",", ";", "\t", "|"])
            delimiter = dialect.delimiter
        except Exception:
            # Fallback heuristic
            counts = {
                ",": text_sample.count(","),
                ";": text_sample.count(";"),
                "\t": text_sample.count("\t"),
                "|": text_sample.count("|"),
            }
            delimiter = max(counts, key=counts.get) if max(counts.values(), default=0) > 0 else ","

        return delimiter, detected_enc

    def read(self, file_path: str, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        delimiter = kwargs.get("delimiter")
        encoding = kwargs.get("encoding")

        if not delimiter or not encoding:
            detected_del, detected_enc = self._detect_delimiter_and_encoding(file_path)
            delimiter = delimiter or detected_del
            encoding = encoding or detected_enc

        # Read CSV with pandas, preserving strings as default or type-inference
        df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, low_memory=False)

        metadata = {
            "format": "CSV",
            "delimiter": delimiter,
            "encoding": encoding,
            "rows": len(df),
            "columns": len(df.columns),
        }
        return df, metadata
