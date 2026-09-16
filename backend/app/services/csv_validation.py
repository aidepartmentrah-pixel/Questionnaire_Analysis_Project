"""CSV upload validation and parsing.

Kept independent of FastAPI so it can be unit-tested directly and reused by
any future entry point (e.g. a CLI) without touching route handlers.
"""

from __future__ import annotations

import csv
import io

import pandas as pd

ALLOWED_EXTENSION = ".csv"


class DatasetValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_and_parse_csv(filename: str, raw_bytes: bytes, max_size_bytes: int) -> pd.DataFrame:
    """Validate an uploaded CSV and return it as a DataFrame, or raise DatasetValidationError."""
    if not filename.lower().endswith(ALLOWED_EXTENSION):
        raise DatasetValidationError("Only .csv files are supported.")

    if len(raw_bytes) == 0:
        raise DatasetValidationError("The uploaded file is empty.")

    if len(raw_bytes) > max_size_bytes:
        limit_mb = max_size_bytes / (1024 * 1024)
        raise DatasetValidationError(f"The uploaded file exceeds the {limit_mb:.0f} MB size limit.")

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DatasetValidationError("The file is not valid UTF-8 text.") from exc

    lines = text.splitlines()
    header_line = lines[0] if lines else ""
    if not header_line.strip():
        raise DatasetValidationError("The CSV file has no header row.")

    header_fields = [field.strip() for field in next(csv.reader([header_line]))]
    if any(not field for field in header_fields):
        raise DatasetValidationError("The CSV header contains an empty column name.")

    duplicate_headers = sorted({name for name in header_fields if header_fields.count(name) > 1})
    if duplicate_headers:
        names = ", ".join(duplicate_headers)
        raise DatasetValidationError(f"The CSV file has duplicate column names: {names}.")

    try:
        df = pd.read_csv(io.StringIO(text))
    except pd.errors.EmptyDataError as exc:
        raise DatasetValidationError("The uploaded file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise DatasetValidationError(
            "The file could not be parsed as CSV. Please check its formatting."
        ) from exc

    if df.shape[1] == 0:
        raise DatasetValidationError("The CSV file has no columns.")

    if df.shape[0] == 0:
        raise DatasetValidationError("The CSV file has no data rows.")

    return df
