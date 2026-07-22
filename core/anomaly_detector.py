"""
AEIA — Pattern & Anomaly Detection Module (Module 4)

Detects outliers using Z-score, IQR, and Isolation Forest methods.
Assigns severity levels and supports threshold breach detection.

FRs implemented: FR-031 through FR-040.
Algorithm parameters: implementation_specification.md §4.
Validation target: sample_data/README.md §6.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger('aeia.anomaly_detector')


# ---------------------------------------------------------------------------
# Severity constants (FR-038, implementation_specification.md §4)
# ---------------------------------------------------------------------------

SEVERITY_INFO = 'Info'
SEVERITY_WARNING = 'Warning'
SEVERITY_CRITICAL = 'Critical'

# Default severity for detection-only anomalies (no matching rule)
# implementation_specification.md §4:
# "Raw Z-score/IQR outliers with no matching rule: default to Warning."
DEFAULT_ANOMALY_SEVERITY = SEVERITY_WARNING


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_anomalies(df: pd.DataFrame,
                     column_types: Dict[str, str],
                     methods: Optional[List[str]] = None,
                     zscore_threshold: float = 3.0,
                     iqr_multiplier: float = 1.5,
                     if_contamination: float = 0.05,
                     if_n_estimators: int = 50,
                     if_random_state: int = 42,
                     if_n_jobs: int = 1,
                     ) -> Dict[str, Any]:
    """Run anomaly detection on all numeric columns.

    FR-034: Allow the user to choose which detection method(s) to run.
    FR-040: All detection runs entirely on CPU with no GPU dependency.

    All threshold parameters come from config/settings.json — never
    hard-coded (code_hygiene_guide.md Rule 6).

    Args:
        df: The cleaned DataFrame.
        column_types: Dict mapping column name → type string.
        methods: List of methods to run. Defaults to all three:
                 ['zscore', 'iqr', 'isolation_forest'].
        zscore_threshold: |z| above this = outlier (FR-031, default 3.0).
        iqr_multiplier: IQR multiplier for bounds (FR-032, default 1.5).
        if_contamination: Isolation Forest contamination (FR-033, default 0.05).
        if_n_estimators: Number of IF trees (FR-033, default 100).
        if_random_state: Fixed seed for reproducibility (FR-033, default 42).

    Returns:
        Dict with keys:
        - 'anomalies': List of anomaly dicts (column, row, method, etc.)
        - 'anomaly_count_by_column': Dict[col → count]
        - 'anomaly_count_by_method': Dict[method → count]
        - 'isolation_forest_flags': Dict[row_index → True] for IF-flagged rows
    """
    if methods is None:
        methods = ['zscore', 'iqr', 'isolation_forest']

    numeric_cols = [
        col for col in df.columns
        if column_types.get(col) == 'numeric'
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    all_anomalies: List[Dict[str, Any]] = []
    if_flags: Dict[int, bool] = {}

    # FR-031: Z-score detection
    if 'zscore' in methods:
        zscore_anomalies = detect_zscore_outliers(
            df, numeric_cols, zscore_threshold
        )
        all_anomalies.extend(zscore_anomalies)

    # FR-032: IQR detection
    if 'iqr' in methods:
        iqr_anomalies = detect_iqr_outliers(
            df, numeric_cols, iqr_multiplier
        )
        all_anomalies.extend(iqr_anomalies)

    # FR-033: Isolation Forest (multivariate)
    if 'isolation_forest' in methods and len(numeric_cols) >= 2:
        if_anomalies, if_flags = detect_isolation_forest(
            df, numeric_cols, if_contamination, if_n_estimators,
            if_random_state, if_n_jobs
        )
        all_anomalies.extend(if_anomalies)

    # Compute summary counts
    by_column: Dict[str, int] = {}
    by_method: Dict[str, int] = {}
    for a in all_anomalies:
        col = a.get('column_name', '')
        method = a.get('method', '')
        by_column[col] = by_column.get(col, 0) + 1
        by_method[method] = by_method.get(method, 0) + 1

    logger.info(
        'Anomaly detection complete: %d anomalies found across %d methods.',
        len(all_anomalies), len(methods)
    )

    return {
        'anomalies': all_anomalies,
        'anomaly_count_by_column': by_column,
        'anomaly_count_by_method': by_method,
        'isolation_forest_flags': if_flags,
    }


# ---------------------------------------------------------------------------
# Z-score detection (FR-031)
# ---------------------------------------------------------------------------

def detect_zscore_outliers(df: pd.DataFrame,
                           numeric_cols: List[str],
                           threshold: float = 3.0
                           ) -> List[Dict[str, Any]]:
    """Detect outliers per numeric column using the Z-score method.

    FR-031: Default threshold |z| > 3, configurable.

    Implementation_specification.md §4:
    z = (value - column_mean) / column_std_dev   # std uses ddof=1
    flag if abs(z) > threshold

    Returns:
        List of anomaly dicts.
    """
    anomalies = []

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 3:
            continue

        mean = series.mean()
        std = series.std()  # ddof=1 (pandas default)
        if std == 0:
            continue

        z_scores = (series - mean) / std

        for idx, z in z_scores.items():
            if abs(z) > threshold:
                anomalies.append({
                    'column_name': col,
                    'row_reference': int(idx) + 2,
                    'method': 'ZScore',
                    'severity': DEFAULT_ANOMALY_SEVERITY,
                    'value': float(df.at[idx, col]),
                    'z_score': round(float(z), 2),
                })

    return anomalies


# ---------------------------------------------------------------------------
# IQR detection (FR-032)
# ---------------------------------------------------------------------------

def detect_iqr_outliers(df: pd.DataFrame,
                        numeric_cols: List[str],
                        multiplier: float = 1.5
                        ) -> List[Dict[str, Any]]:
    """Detect outliers per numeric column using the IQR method.

    FR-032: Default 1.5×IQR, configurable.

    Implementation_specification.md §4:
    Q1, Q3 = 25th and 75th percentile
    IQR = Q3 - Q1
    lower = Q1 - multiplier * IQR
    upper = Q3 + multiplier * IQR
    flag if value < lower or value > upper

    Returns:
        List of anomaly dicts.
    """
    anomalies = []

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        for idx, val in series.items():
            if val < lower_bound or val > upper_bound:
                anomalies.append({
                    'column_name': col,
                    'row_reference': int(idx) + 2,
                    'method': 'IQR',
                    'severity': DEFAULT_ANOMALY_SEVERITY,
                    'value': float(val),
                    'lower_bound': round(float(lower_bound), 2),
                    'upper_bound': round(float(upper_bound), 2),
                })

    return anomalies


# ---------------------------------------------------------------------------
# Isolation Forest detection (FR-033)
# ---------------------------------------------------------------------------

def detect_isolation_forest(df: pd.DataFrame,
                            numeric_cols: List[str],
                            contamination: float = 0.05,
                            n_estimators: int = 50,
                            random_state: int = 42,
                            n_jobs: int = 1,
                            ) -> Tuple[List[Dict[str, Any]], Dict[int, bool]]:
    """Detect multivariate anomalies using Isolation Forest.

    FR-033: Detect multivariate anomalies using an Isolation Forest model
    (scikit-learn) across selected numeric columns.

    Implementation_specification.md §4:
    Run across ALL selected numeric columns simultaneously (multivariate).
    predictions == -1 => anomaly.

    Returns:
        Tuple of (anomaly list, flag dict mapping row_index → True).
    """
    anomalies = []
    flags: Dict[int, bool] = {}

    if len(numeric_cols) < 2:
        logger.info('Skipping Isolation Forest: need ≥2 numeric columns.')
        return anomalies, flags

    # Prepare the data matrix — drop rows with any NaN in numeric cols
    data = df[numeric_cols].copy()
    valid_mask = data.notna().all(axis=1)
    clean_data = data[valid_mask]

    if len(clean_data) < 10:
        logger.info(
            'Skipping Isolation Forest: only %d valid rows (need ≥10).',
            len(clean_data)
        )
        return anomalies, flags

    # FR-033: Build and fit the model
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    predictions = model.fit_predict(clean_data)

    # -1 = anomaly, 1 = normal
    for i, (idx, pred) in enumerate(zip(clean_data.index, predictions)):
        if pred == -1:
            flags[int(idx) + 2] = True
            anomalies.append({
                'column_name': ','.join(numeric_cols),
                'row_reference': int(idx) + 2,
                'method': 'IsolationForest',
                'severity': DEFAULT_ANOMALY_SEVERITY,
                'value': None,  # Multivariate — no single value
                'columns_involved': numeric_cols,
            })

    logger.info(
        'Isolation Forest: flagged %d / %d rows as anomalies.',
        len(anomalies), len(clean_data)
    )

    return anomalies, flags


# ---------------------------------------------------------------------------
# Severity assignment utility (shared by expert_system and
# recommendation_engine — Code Hygiene Rule 2: DRY)
# ---------------------------------------------------------------------------

def assign_severity(base_severity: str,
                    rule_severity: Optional[str] = None) -> str:
    """Determine the final severity for a finding.

    FR-038: Assign severity (Info / Warning / Critical) based on rules.

    Implementation_specification.md §4:
    - Rule-based findings: use the rule's own severity.
    - Detection-only findings (no matching rule): default to Warning.

    Args:
        base_severity: The default severity from the detection method.
        rule_severity: If a rule matched, its severity overrides the default.

    Returns:
        One of: 'Info', 'Warning', 'Critical'.
    """
    if rule_severity is not None:
        return rule_severity
    return base_severity
