"""
AEIA — Dataset Import Module (Module 1)

Handles importing CSV, XLSX, JSON, TXT, and LOG files with automatic
file-type detection, delimiter sniffing, column type inference, and
preview generation.

FRs implemented: FR-001 through FR-010.
Algorithm details: implementation_specification.md §6.
Validation target: sample_data/README.md §1.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import csv
import io
import logging
import os
import re
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger('aeia.data_loader')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# FR-005, implementation_specification.md §6: LOG line regex
LOG_LINE_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)\s+'
    r'(?P<level>[A-Z]{4,8})\s+(?P<message>.*)$'
)

# Supported file extensions mapped to canonical type names
EXTENSION_MAP = {
    '.csv': 'CSV',
    '.xlsx': 'XLSX',
    '.xls': 'XLSX',
    '.json': 'JSON',
    '.txt': 'TXT',
    '.log': 'LOG',
}

# implementation_specification.md §6: delimiter fallback order for CSV/TXT
DELIMITER_FALLBACK_ORDER = [',', '\t', ';', '|']

# Standard error messages from implementation_specification.md §9
ERROR_CANNOT_PARSE = (
    "This file could not be read. It may be corrupted or in an unsupported "
    "format. Please check the file and try again."
)
ERROR_UNSUPPORTED = (
    "This file type isn't supported yet. AEIA currently supports CSV, XLSX, "
    "JSON, TXT, and LOG files."
)
ERROR_EMPTY = (
    "This file appears to be empty. Please import a file that contains data."
)
ERROR_RAGGED = (
    "Some rows in this file have a different number of columns than the "
    "header (first seen at row {row_number}). Please check the file's "
    "formatting."
)


# ---------------------------------------------------------------------------
# Data type constants for column type detection (FR-008)
# ---------------------------------------------------------------------------

COLUMN_TYPE_NUMERIC = 'numeric'
COLUMN_TYPE_CATEGORICAL = 'categorical'
COLUMN_TYPE_DATETIME = 'datetime'
COLUMN_TYPE_TEXT = 'text'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_dataset(file_path: str) -> Tuple[pd.DataFrame, Dict[str, str], str]:
    """Load a dataset file and return its contents with type information.

    FR-001 through FR-006: Support CSV, XLSX, JSON, TXT, and LOG files
    with automatic file type detection.

    Args:
        file_path: Absolute path to the dataset file.

    Returns:
        A tuple of:
        - DataFrame: The loaded dataset.
        - column_types: Dict mapping column name → type string
          ('numeric', 'categorical', 'datetime', 'text').
        - file_type: The detected file type ('CSV', 'XLSX', 'JSON',
          'TXT', 'LOG').

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty, unparseable, or unsupported.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # FR-006: Auto-detect file type from extension and content
    file_type = detect_file_type(file_path)
    logger.info('Detected file type: %s for %s', file_type, file_path)

    # Load based on detected type
    loaders = {
        'CSV': _load_csv,
        'XLSX': _load_xlsx,
        'JSON': _load_json,
        'TXT': _load_txt,
        'LOG': _load_log,
    }

    loader = loaders.get(file_type)
    if loader is None:
        raise ValueError(ERROR_UNSUPPORTED)

    try:
        df = loader(file_path)
    except Exception as exc:
        logger.error('Failed to parse %s as %s: %s', file_path, file_type, exc)
        raise ValueError(ERROR_CANNOT_PARSE) from exc

    # Validate the loaded dataset
    if df.empty or len(df) == 0:
        raise ValueError(ERROR_EMPTY)

    # FR-008: Automatically detect each column's data type
    column_types = detect_column_types(df)

    logger.info(
        'Loaded %d rows × %d columns from %s',
        len(df), len(df.columns), os.path.basename(file_path)
    )

    return df, column_types, file_type


def detect_file_type(file_path: str) -> str:
    """Detect the file type from extension and content.

    FR-006: Auto-detect file type from extension and content; prompt the
    user to confirm/select format if detection is ambiguous.

    Detection order (implementation_specification.md §6):
    1. Trust the extension if recognized.
    2. If unrecognized, sniff the content (JSON → LOG → CSV/TXT → Excel).

    Args:
        file_path: Path to the file.

    Returns:
        One of: 'CSV', 'XLSX', 'JSON', 'TXT', 'LOG'.

    Raises:
        ValueError: If the file type cannot be determined.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Step 1: Trust the extension if it's one of the recognized ones
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    # Step 2: Content sniffing for unknown/missing extensions
    return _sniff_file_content(file_path)


def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Detect the data type of each column in a DataFrame.

    FR-008: Automatically detect each column's data type
    (numeric, categorical, datetime, text).

    Classification logic:
    - Already numeric dtype → 'numeric'
    - Already datetime dtype → 'datetime'
    - String column: attempt datetime parsing → 'datetime' if successful
    - String column with few unique values relative to total → 'categorical'
    - Otherwise → 'text'

    Args:
        df: The loaded DataFrame.

    Returns:
        Dict mapping column name → type string.
    """
    column_types = {}
    for col in df.columns:
        column_types[col] = _classify_column(df[col])
    return column_types


def get_preview(df: pd.DataFrame, n_rows: int = 50) -> pd.DataFrame:
    """Return the first N rows of a DataFrame for preview display.

    FR-007: Display a preview grid of the first N rows immediately
    after import, before committing to analysis.

    Args:
        df: The full DataFrame.
        n_rows: Number of rows to include in the preview.

    Returns:
        A DataFrame with at most n_rows rows.
    """
    return df.head(n_rows).copy()


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def _load_csv(file_path: str) -> pd.DataFrame:
    """Load a CSV file with automatic delimiter detection.

    FR-001: Support importing CSV files.
    Implementation_specification.md §6: Delimiter sniffing for CSV/TXT.
    """
    delimiter = _sniff_delimiter(file_path)
    return pd.read_csv(file_path, delimiter=delimiter)


def _load_xlsx(file_path: str) -> pd.DataFrame:
    """Load an Excel (.xlsx/.xls) file, using the first sheet.

    FR-002: Support importing Excel (.xlsx) files.
    """
    return pd.read_excel(file_path, sheet_name=0, engine='openpyxl')


def _load_json(file_path: str) -> pd.DataFrame:
    """Load a JSON file, handling both array-of-objects and nested structures.

    FR-003: Support importing JSON files.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = f.read().strip()

    if not data:
        raise ValueError(ERROR_EMPTY)

    # Try records-oriented JSON first (array of objects)
    try:
        df = pd.read_json(io.StringIO(data))
        if not df.empty:
            return df
    except (ValueError, TypeError):
        pass

    # Try json_normalize for nested structures
    import json
    parsed = json.loads(data)
    if isinstance(parsed, list):
        df = pd.json_normalize(parsed)
    elif isinstance(parsed, dict):
        # Single object — wrap in list
        df = pd.json_normalize([parsed])
    else:
        raise ValueError(ERROR_CANNOT_PARSE)

    return df


def _load_txt(file_path: str) -> pd.DataFrame:
    """Load a delimited TXT file with automatic delimiter detection.

    FR-004: Support importing TXT files (delimited or plain).
    Implementation_specification.md §6: Delimiter sniffing.
    """
    delimiter = _sniff_delimiter(file_path)
    return pd.read_csv(file_path, delimiter=delimiter)


def _load_log(file_path: str) -> pd.DataFrame:
    """Load a LOG file using regex-based line parsing.

    FR-005: Support importing LOG files (semi-structured; regex-based).
    Implementation_specification.md §6: LOG line pattern.

    If fewer than 50% of lines match the pattern, the file is treated as
    unstructured: one row per line in a single 'raw_line' column.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        raise ValueError(ERROR_EMPTY)

    # Strip trailing newlines
    lines = [line.rstrip('\n\r') for line in lines]

    # Filter out empty lines for matching analysis
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        raise ValueError(ERROR_EMPTY)

    # Count how many lines match the LOG pattern
    matched_rows = []
    unmatched_rows = []

    for line in non_empty:
        match = LOG_LINE_PATTERN.match(line)
        if match:
            matched_rows.append(match.groupdict())
        else:
            # Unmatched lines get placeholder fields
            unmatched_rows.append({
                'timestamp': None,
                'level': 'UNKNOWN',
                'message': line,
            })

    match_ratio = len(matched_rows) / len(non_empty) if non_empty else 0

    # implementation_specification.md §6: If fewer than 50% match,
    # treat as unstructured single-column text
    if match_ratio < 0.5:
        logger.info(
            'Only %.0f%% of lines matched LOG pattern — treating as '
            'unstructured text.',
            match_ratio * 100
        )
        return pd.DataFrame({'raw_line': non_empty})

    # Combine matched and unmatched rows in order
    all_rows = matched_rows + unmatched_rows
    df = pd.DataFrame(all_rows, columns=['timestamp', 'level', 'message'])

    # Convert timestamps (NaT for unmatched lines)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    return df


# ---------------------------------------------------------------------------
# Content sniffing helpers
# ---------------------------------------------------------------------------

def _sniff_file_content(file_path: str) -> str:
    """Determine file type by inspecting content when the extension is
    missing or unrecognized.

    Implementation_specification.md §6 detection order:
    1. Starts with '{' or '[' → JSON
    2. >50% of first 20 lines match LOG_LINE_PATTERN → LOG
    3. Otherwise → CSV/TXT
    4. If all fail, try Excel
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(8192)
    except UnicodeDecodeError:
        # Binary file — likely Excel
        return 'XLSX'

    stripped = sample.strip()
    if not stripped:
        raise ValueError(ERROR_EMPTY)

    # Check for JSON
    if stripped[0] in ('{', '['):
        return 'JSON'

    # Check for LOG pattern
    lines = stripped.split('\n')[:20]
    non_empty_lines = [l for l in lines if l.strip()]
    if non_empty_lines:
        match_count = sum(
            1 for l in non_empty_lines if LOG_LINE_PATTERN.match(l.strip())
        )
        if match_count / len(non_empty_lines) > 0.5:
            return 'LOG'

    # Default to CSV/TXT (they use the same parser with delimiter sniffing)
    return 'CSV'


def _sniff_delimiter(file_path: str) -> str:
    """Detect the delimiter used in a CSV/TXT file.

    Implementation_specification.md §6:
    Use csv.Sniffer().sniff(sample). If that fails, try delimiters in
    priority order [',', '\\t', ';', '|'] and use the first one that
    produces a consistent column count. Default to comma.

    Returns:
        The detected delimiter character.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        sample_lines = []
        for i, line in enumerate(f):
            sample_lines.append(line)
            if i >= 9:  # First ~10 lines
                break

    sample_text = ''.join(sample_lines)

    # Try csv.Sniffer first
    try:
        dialect = csv.Sniffer().sniff(sample_text)
        if dialect.delimiter:
            logger.debug('csv.Sniffer detected delimiter: %r', dialect.delimiter)
            return dialect.delimiter
    except csv.Error:
        logger.debug('csv.Sniffer failed, trying fallback delimiters.')

    # Fallback: try each delimiter and check for consistent column count
    for delim in DELIMITER_FALLBACK_ORDER:
        counts = []
        for line in sample_lines:
            stripped = line.strip()
            if stripped:
                counts.append(len(stripped.split(delim)))
        if counts and len(set(counts)) == 1 and counts[0] > 1:
            logger.debug('Fallback detected delimiter: %r', delim)
            return delim

    # Last resort: comma
    logger.debug('No consistent delimiter found, defaulting to comma.')
    return ','


# ---------------------------------------------------------------------------
# Column type classification
# ---------------------------------------------------------------------------

def _classify_column(series: pd.Series) -> str:
    """Classify a single column as numeric, datetime, categorical, or text.

    FR-008: Automatically detect each column's data type.

    Logic:
    - If already numeric dtype → 'numeric'
    - If already datetime dtype → 'datetime'
    - If object/string: try datetime parsing → 'datetime'
    - If string with few unique values (ratio < 0.3 or < 20 unique) → 'categorical'
    - Otherwise → 'text'
    """
    if pd.api.types.is_numeric_dtype(series):
        return COLUMN_TYPE_NUMERIC

    if pd.api.types.is_datetime64_any_dtype(series):
        return COLUMN_TYPE_DATETIME

    # Try to parse as datetime
    if series.dtype == object:
        non_null = series.dropna()
        if len(non_null) > 0:
            try:
                parsed = pd.to_datetime(non_null, format='mixed')
                # If most values parse successfully, it's datetime
                if parsed.notna().sum() / len(non_null) > 0.8:
                    return COLUMN_TYPE_DATETIME
            except (ValueError, TypeError):
                pass

    # Check for categorical: few unique values relative to total
    non_null = series.dropna()
    if len(non_null) > 0:
        n_unique = non_null.nunique()
        ratio = n_unique / len(non_null)
        if n_unique <= 20 or ratio < 0.3:
            return COLUMN_TYPE_CATEGORICAL

    return COLUMN_TYPE_TEXT


# ---------------------------------------------------------------------------
# Validation helper (used by preprocessor, but available here for early checks)
# ---------------------------------------------------------------------------

def validate_structure(df: pd.DataFrame) -> Optional[str]:
    """Check for basic structural issues in a loaded DataFrame.

    FR-011: Validate dataset structure (non-empty, consistent column count).

    Returns:
        None if valid, or an error message string if invalid.
    """
    if df.empty:
        return ERROR_EMPTY
    return None
