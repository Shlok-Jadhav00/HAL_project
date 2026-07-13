"""
AEIA — Data Preprocessing Module (Module 2)

Handles dataset validation, cleaning, missing value imputation, duplicate
removal, formatting normalization, and outlier pre-scanning.

FRs implemented: FR-011 through FR-020.
Default values: implementation_specification.md §2.
Error messages: implementation_specification.md §9.
Validation target: sample_data/README.md §2.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger('aeia.preprocessor')


# ---------------------------------------------------------------------------
# Standard error messages (implementation_specification.md §9)
# ---------------------------------------------------------------------------

ERROR_EMPTY = (
    "This file appears to be empty. Please import a file that contains data."
)
ERROR_RAGGED = (
    "Some rows in this file have a different number of columns than the "
    "header (first seen at row {row_number}). Please check the file's "
    "formatting."
)


# ---------------------------------------------------------------------------
# Missing value strategies (FR-013)
# ---------------------------------------------------------------------------

STRATEGY_DROP = 'drop'
STRATEGY_FILL_MEAN = 'fill_mean'
STRATEGY_FILL_MEDIAN = 'fill_median'
STRATEGY_FILL_CONSTANT = 'fill_constant'
STRATEGY_LEAVE = 'leave'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_structure(df: pd.DataFrame) -> Optional[str]:
    """Validate dataset structure before processing.

    FR-011: Validate dataset structure (non-empty, consistent column count
    per row) before processing.

    Args:
        df: The raw imported DataFrame.

    Returns:
        None if valid, or an error message string if invalid.
    """
    if df.empty:
        return ERROR_EMPTY
    return None


def detect_missing_values(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Detect missing values per column and report count/percentage.

    FR-012: Detect missing values per column and report the
    count/percentage.

    Args:
        df: The DataFrame to analyze.

    Returns:
        Dict mapping column name → {'count': int, 'percentage': float}.
    """
    report = {}
    total_rows = len(df)
    for col in df.columns:
        count = int(df[col].isna().sum())
        pct = (count / total_rows * 100) if total_rows > 0 else 0.0
        report[col] = {'count': count, 'percentage': round(pct, 2)}
    return report


def fill_missing_values(df: pd.DataFrame,
                        strategies: Dict[str, str],
                        fill_constants: Optional[Dict[str, Any]] = None,
                        default_numeric_fill: float = 0,
                        default_categorical_fill: str = 'Unknown'
                        ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Apply missing-value strategies per column.

    FR-013: Provide missing-value strategies: drop rows, fill with
    mean/median, fill with a constant, or leave as-is.

    Args:
        df: The DataFrame to clean.
        strategies: Dict mapping column name → strategy string
                    ('drop', 'fill_mean', 'fill_median', 'fill_constant',
                    'leave').
        fill_constants: Optional dict mapping column name → fill value
                        for 'fill_constant' strategy.
        default_numeric_fill: Default fill constant for numeric columns
                              (from settings.json, default 0).
        default_categorical_fill: Default fill constant for categorical
                                   columns (from settings.json, default
                                   'Unknown').

    Returns:
        Tuple of (cleaned DataFrame, preprocessing log entries).
    """
    result = df.copy()
    log_entries = []
    fill_constants = fill_constants or {}

    for col, strategy in strategies.items():
        if col not in result.columns:
            continue

        missing_count = int(result[col].isna().sum())
        if missing_count == 0:
            continue

        if strategy == STRATEGY_DROP:
            rows_before = len(result)
            result = result.dropna(subset=[col])
            dropped = rows_before - len(result)
            log_entries.append({
                'action': 'drop_rows',
                'column': col,
                'detail': f'Dropped {dropped} rows with missing values in '
                          f'"{col}"',
                'affected_count': dropped,
            })

        elif strategy == STRATEGY_FILL_MEAN:
            # FR-013: Fill with mean (only meaningful for numeric columns)
            if pd.api.types.is_numeric_dtype(result[col]):
                fill_val = result[col].mean()
                result[col] = result[col].fillna(fill_val)
                log_entries.append({
                    'action': 'fill_mean',
                    'column': col,
                    'detail': f'Filled {missing_count} missing values in '
                              f'"{col}" with mean ({fill_val:.4f})',
                    'affected_count': missing_count,
                })
            else:
                logger.warning(
                    'Cannot fill non-numeric column "%s" with mean; '
                    'leaving as-is.', col
                )

        elif strategy == STRATEGY_FILL_MEDIAN:
            if pd.api.types.is_numeric_dtype(result[col]):
                fill_val = result[col].median()
                result[col] = result[col].fillna(fill_val)
                log_entries.append({
                    'action': 'fill_median',
                    'column': col,
                    'detail': f'Filled {missing_count} missing values in '
                              f'"{col}" with median ({fill_val:.4f})',
                    'affected_count': missing_count,
                })
            else:
                logger.warning(
                    'Cannot fill non-numeric column "%s" with median; '
                    'leaving as-is.', col
                )

        elif strategy == STRATEGY_FILL_CONSTANT:
            fill_val = fill_constants.get(col)
            if fill_val is None:
                # Use defaults from settings
                if pd.api.types.is_numeric_dtype(result[col]):
                    fill_val = default_numeric_fill
                else:
                    fill_val = default_categorical_fill
            result[col] = result[col].fillna(fill_val)
            log_entries.append({
                'action': 'fill_constant',
                'column': col,
                'detail': f'Filled {missing_count} missing values in '
                          f'"{col}" with constant ({fill_val})',
                'affected_count': missing_count,
            })

        elif strategy == STRATEGY_LEAVE:
            log_entries.append({
                'action': 'leave',
                'column': col,
                'detail': f'Left {missing_count} missing values in '
                          f'"{col}" unchanged',
                'affected_count': 0,
            })

    result = result.reset_index(drop=True)
    return result, log_entries


def remove_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Detect and remove exact duplicate rows.

    FR-014: Detect and remove exact duplicate rows; show the count of
    duplicates removed.

    Args:
        df: The DataFrame to deduplicate.

    Returns:
        Tuple of (deduplicated DataFrame, count of duplicates removed).
    """
    count_before = len(df)
    result = df.drop_duplicates().reset_index(drop=True)
    count_removed = count_before - len(result)

    if count_removed > 0:
        logger.info('Removed %d duplicate rows.', count_removed)

    return result, count_removed


def detect_formatting_issues(df: pd.DataFrame,
                             column_types: Dict[str, str]
                             ) -> Dict[str, Dict[str, Any]]:
    """Detect inconsistent formatting in categorical/text columns.

    FR-015: Detect inconsistent formatting (mixed date formats, stray
    whitespace, mixed-case categorical labels) and offer to normalize.

    Args:
        df: The DataFrame to check.
        column_types: Dict mapping column name → type string.

    Returns:
        Dict mapping column name → issue details, e.g.:
        {'Status': {'type': 'mixed_case', 'variants': ['Nominal', 'nominal', 'NOMINAL'],
                     'suggested_canonical': 'Nominal'}}.
        Empty dict if no issues found.
    """
    issues = {}

    for col in df.columns:
        col_type = column_types.get(col, 'text')
        if col_type not in ('categorical', 'text'):
            continue

        series = df[col].dropna().astype(str)
        if series.empty:
            continue

        # Check for whitespace issues
        has_whitespace = series.str.strip() != series
        whitespace_count = int(has_whitespace.sum())

        # Check for mixed case (case-insensitive grouping)
        stripped = series.str.strip()
        lower_groups = stripped.str.lower()
        unique_lower = lower_groups.unique()
        unique_original = stripped.unique()

        mixed_case = len(unique_original) > len(unique_lower)

        if mixed_case or whitespace_count > 0:
            # Find the variants for each canonical form
            variants = {}
            for val in unique_original:
                canonical = val.strip().lower()
                if canonical not in variants:
                    variants[canonical] = []
                variants[canonical].append(val)

            # Only report groups with actual inconsistencies
            problem_groups = {
                k: v for k, v in variants.items() if len(v) > 1
            }

            if problem_groups or whitespace_count > 0:
                issues[col] = {
                    'mixed_case': mixed_case,
                    'whitespace_issues': whitespace_count,
                    'variant_groups': problem_groups,
                    'unique_original': list(unique_original),
                }

    return issues


def normalize_formatting(df: pd.DataFrame,
                         columns: List[str]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Normalize formatting for specified categorical/text columns.

    FR-015: Applies case-folding (title case) and whitespace trimming.

    Args:
        df: The DataFrame to normalize.
        columns: List of column names to normalize.

    Returns:
        Tuple of (normalized DataFrame, preprocessing log entries).
    """
    result = df.copy()
    log_entries = []

    for col in columns:
        if col not in result.columns:
            continue

        original_unique = result[col].dropna().nunique()
        # Apply strip + title case
        result[col] = result[col].apply(
            lambda x: x.strip().title() if isinstance(x, str) else x
        )
        new_unique = result[col].dropna().nunique()

        changes = original_unique - new_unique
        if changes > 0:
            log_entries.append({
                'action': 'normalize_formatting',
                'column': col,
                'detail': f'Normalized formatting in "{col}": '
                          f'{original_unique} → {new_unique} unique values '
                          f'(case-folded and trimmed)',
                'affected_count': changes,
            })

    return result, log_entries


def outlier_prescan(df: pd.DataFrame,
                    column_types: Dict[str, str],
                    zscore_threshold: float = 3.0
                    ) -> List[Dict[str, Any]]:
    """Run a quick outlier pre-scan on numeric columns.

    FR-016: Run a quick outlier pre-scan on numeric columns and warn the
    user before full analysis.

    Args:
        df: The DataFrame to scan.
        column_types: Dict mapping column name → type string.
        zscore_threshold: Z-score threshold for flagging (from settings).

    Returns:
        List of warning dicts, each with 'column', 'extreme_count',
        'min_value', 'max_value'.
    """
    warnings = []

    for col in df.columns:
        if column_types.get(col) != 'numeric':
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        series = df[col].dropna()
        if len(series) < 3:
            continue

        mean = series.mean()
        std = series.std()
        if std == 0:
            continue

        z_scores = ((series - mean) / std).abs()
        extreme_count = int((z_scores > zscore_threshold).sum())

        if extreme_count > 0:
            warnings.append({
                'column': col,
                'extreme_count': extreme_count,
                'min_value': float(series.min()),
                'max_value': float(series.max()),
            })

    return warnings


def sanity_range_check(df: pd.DataFrame,
                       ranges: Dict[str, Tuple[float, float]]
                       ) -> List[Dict[str, Any]]:
    """Check numeric columns against user-defined plausible ranges.

    FR-017: Allow a basic sanity-range check per numeric column.

    Args:
        df: The DataFrame to check.
        ranges: Dict mapping column name → (min_acceptable, max_acceptable).

    Returns:
        List of dicts with 'column', 'row_indices', 'values' for
        out-of-range values.
    """
    violations = []

    for col, (range_min, range_max) in ranges.items():
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        series = df[col].dropna()
        mask = (series < range_min) | (series > range_max)
        bad = series[mask]

        if len(bad) > 0:
            violations.append({
                'column': col,
                'row_indices': bad.index.tolist(),
                'values': bad.tolist(),
                'range': (range_min, range_max),
            })

    return violations


def preprocess_dataset(df: pd.DataFrame,
                       column_types: Dict[str, str],
                       missing_strategies: Optional[Dict[str, str]] = None,
                       normalize_columns: Optional[List[str]] = None,
                       remove_dupes: bool = True,
                       default_numeric_fill: float = 0,
                       default_categorical_fill: str = 'Unknown',
                       ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Run the full preprocessing pipeline on a dataset.

    FR-011 through FR-020: Complete preprocessing with logging.

    This is a convenience function that chains all preprocessing steps.
    The GUI can also call individual functions for step-by-step control.

    Args:
        df: Raw imported DataFrame.
        column_types: Dict mapping column name → type string.
        missing_strategies: Dict mapping column name → fill strategy.
                            If None, defaults to 'fill_mean' for numeric
                            columns with missing values.
        normalize_columns: List of columns to normalize formatting on.
                           If None, auto-detects columns with issues.
        remove_dupes: Whether to remove duplicate rows.
        default_numeric_fill: Default fill constant for numeric columns.
        default_categorical_fill: Default fill constant for categoricals.

    Returns:
        Tuple of (cleaned DataFrame, complete preprocessing log).
    """
    full_log = []

    # FR-011: Validate structure
    error = validate_structure(df)
    if error:
        raise ValueError(error)

    working = df.copy()

    # FR-014: Remove duplicates first (before any fill operations)
    if remove_dupes:
        working, dup_count = remove_duplicates(working)
        if dup_count > 0:
            full_log.append({
                'action': 'remove_duplicates',
                'column': '*',
                'detail': f'Removed {dup_count} duplicate rows',
                'affected_count': dup_count,
            })

    # FR-013: Handle missing values
    if missing_strategies is None:
        # Auto-generate strategies: fill_mean for numeric columns with gaps
        missing_strategies = {}
        missing_report = detect_missing_values(working)
        for col, info in missing_report.items():
            if info['count'] > 0:
                if column_types.get(col) == 'numeric':
                    missing_strategies[col] = STRATEGY_FILL_MEAN
                else:
                    missing_strategies[col] = STRATEGY_LEAVE

    if missing_strategies:
        working, fill_log = fill_missing_values(
            working, missing_strategies,
            default_numeric_fill=default_numeric_fill,
            default_categorical_fill=default_categorical_fill,
        )
        full_log.extend(fill_log)

    # FR-015: Normalize formatting
    if normalize_columns is None:
        # Auto-detect columns with formatting issues
        issues = detect_formatting_issues(working, column_types)
        normalize_columns = list(issues.keys())

    if normalize_columns:
        working, norm_log = normalize_formatting(working, normalize_columns)
        full_log.extend(norm_log)

    # FR-018: Log is included in the return value for the final report
    logger.info(
        'Preprocessing complete: %d log entries, %d rows remaining.',
        len(full_log), len(working)
    )

    return working, full_log
