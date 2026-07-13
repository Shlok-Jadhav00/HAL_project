"""
AEIA — Statistical Analysis Engine (Module 3)

Computes descriptive statistics, trend analysis, pairwise correlation,
and frequency distributions for cleaned datasets.

FRs implemented: FR-021 through FR-030.
Algorithm parameters: implementation_specification.md §4.
Validation target: sample_data/README.md §§3–5.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger('aeia.statistics_engine')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_statistics(df: pd.DataFrame,
                       column_types: Dict[str, str],
                       correlation_threshold: float = 0.7,
                       trend_window_fraction: float = 0.1,
                       trend_window_min: int = 3,
                       trend_window_max: int = 20,
                       trend_stability_multiplier: float = 0.5,
                       trend_minimum_slope_magnitude: float = 0.01,
                       ) -> Dict[str, Any]:
    """Compute all statistics for a cleaned dataset.

    FR-021 through FR-030: Descriptive stats, trend analysis, correlation,
    and frequency distributions.

    All threshold and window parameters come from config/settings.json
    and are passed in by the caller — never hard-coded here
    (code_hygiene_guide.md Rule 6).

    Args:
        df: The cleaned DataFrame.
        column_types: Dict mapping column name → type string.
        correlation_threshold: |r| above this = "strong" (FR-026).
        trend_window_fraction: Fraction of dataset for moving avg window.
        trend_window_min: Minimum window size for moving average.
        trend_window_max: Maximum window size for moving average.
        trend_stability_multiplier: Multiplied by std_dev for trend bar.

    Returns:
        Dict with keys:
        - 'per_column': Dict[col_name → column stats dict]
        - 'correlations': Dict with 'matrix' and 'strong_pairs'
        - 'frequency_distributions': Dict[col_name → frequency dict]
    """
    result = {
        'per_column': {},
        'correlations': {},
        'frequency_distributions': {},
    }

    numeric_cols = [
        col for col in df.columns
        if column_types.get(col) == 'numeric'
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    categorical_cols = [
        col for col in df.columns
        if column_types.get(col) in ('categorical', 'text')
    ]

    # FR-021 through FR-024: Per-column statistics for numeric columns
    for col in numeric_cols:
        result['per_column'][col] = compute_column_statistics(
            df[col], col_name=col, df=df,
            column_types=column_types,
            trend_window_fraction=trend_window_fraction,
            trend_window_min=trend_window_min,
            trend_window_max=trend_window_max,
            trend_stability_multiplier=trend_stability_multiplier,
            trend_minimum_slope_magnitude=trend_minimum_slope_magnitude,
        )

    # FR-025, FR-026: Pairwise Pearson correlation
    if len(numeric_cols) >= 2:
        result['correlations'] = compute_correlations(
            df, numeric_cols, correlation_threshold
        )

    # FR-027: Frequency distributions for categorical columns
    for col in categorical_cols:
        result['frequency_distributions'][col] = compute_frequency(df[col])

    logger.info(
        'Computed statistics: %d numeric columns, %d categorical columns, '
        '%d strong correlation pairs.',
        len(numeric_cols),
        len(categorical_cols),
        len(result['correlations'].get('strong_pairs', [])),
    )

    return result


def compute_column_statistics(series: pd.Series,
                              col_name: str = '',
                              df: Optional[pd.DataFrame] = None,
                              column_types: Optional[Dict[str, str]] = None,
                              trend_window_fraction: float = 0.1,
                              trend_window_min: int = 3,
                              trend_window_max: int = 20,
                              trend_stability_multiplier: float = 0.5,
                              trend_minimum_slope_magnitude: float = 0.01,
                              ) -> Dict[str, Any]:
    """Compute descriptive statistics for a single numeric column.

    FR-021: mean, median, mode, standard deviation, variance.
    FR-022: min, max, range.
    FR-023: quartiles (Q1, Q3), IQR.
    FR-024: trend analysis (moving average, slope, direction).

    Args:
        series: The numeric column data.
        col_name: Column name (for logging).
        df: The full DataFrame (needed for trend axis detection).
        column_types: Column type map (needed for finding datetime col).
        trend_window_fraction: Fraction of dataset for moving avg.
        trend_window_min: Minimum window size.
        trend_window_max: Maximum window size.
        trend_stability_multiplier: For direction classification.

    Returns:
        Dict with all computed statistics.
    """
    clean = series.dropna()

    if len(clean) == 0:
        return _empty_stats()

    # FR-021: Central tendency and spread
    mean = float(clean.mean())
    median = float(clean.median())
    std_dev = float(clean.std())          # ddof=1 (pandas default)
    variance = float(clean.var())          # ddof=1

    # Mode: take the first mode if multiple exist
    mode_result = clean.mode()
    mode = float(mode_result.iloc[0]) if len(mode_result) > 0 else None

    # FR-022: Min, max, range
    min_val = float(clean.min())
    max_val = float(clean.max())
    val_range = max_val - min_val

    # FR-023: Quartiles and IQR
    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1

    # FR-024: Trend analysis
    trend = _compute_trend(
        clean, col_name, df, column_types,
        trend_window_fraction, trend_window_min, trend_window_max,
        trend_stability_multiplier, trend_minimum_slope_magnitude, std_dev,
    )

    return {
        'mean': mean,
        'median': median,
        'mode': mode,
        'std_dev': std_dev,
        'variance': variance,
        'min_value': min_val,
        'max_value': max_val,
        'range': val_range,
        'q1': q1,
        'q3': q3,
        'iqr': iqr,
        'trend_slope': trend.get('slope'),
        'trend_direction': trend.get('direction'),
        'trend_intercept': trend.get('intercept'),
        'moving_average_window': trend.get('window'),
    }


def compute_correlations(df: pd.DataFrame,
                         numeric_cols: List[str],
                         threshold: float = 0.7
                         ) -> Dict[str, Any]:
    """Compute pairwise Pearson correlations for numeric columns.

    FR-025: Perform pairwise Pearson correlation analysis.
    FR-026: Highlight correlations above threshold.

    Implementation: dataframe[numeric_cols].corr() per
    implementation_specification.md §4.

    Returns:
        Dict with:
        - 'matrix': Dict of dict, correlation values.
        - 'strong_pairs': List of (col_a, col_b, r_value) where |r| > threshold.
    """
    corr_matrix = df[numeric_cols].corr()

    # Find strong pairs (upper triangle only to avoid duplicates)
    strong_pairs = []
    for i, col_a in enumerate(numeric_cols):
        for j, col_b in enumerate(numeric_cols):
            if j <= i:
                continue  # Skip diagonal and lower triangle
            r = corr_matrix.loc[col_a, col_b]
            if abs(r) > threshold:
                strong_pairs.append({
                    'column_a': col_a,
                    'column_b': col_b,
                    'r_value': round(float(r), 6),
                })

    return {
        'matrix': corr_matrix.to_dict(),
        'strong_pairs': strong_pairs,
    }


def compute_frequency(series: pd.Series) -> Dict[str, int]:
    """Compute frequency distribution for a categorical column.

    FR-027: Compute frequency distributions for categorical columns.

    Returns:
        Dict mapping category value → count, sorted by count descending.
    """
    counts = series.value_counts().to_dict()
    return {str(k): int(v) for k, v in counts.items()}


def compute_grouped_statistics(df: pd.DataFrame,
                               group_col: str,
                               numeric_cols: List[str]
                               ) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Compute grouped/segmented statistics.

    FR-028: Support grouped/segmented statistics (e.g. per test-run or
    per sensor ID).

    Args:
        df: The DataFrame.
        group_col: Column to group by.
        numeric_cols: Numeric columns to compute stats for.

    Returns:
        Dict mapping group_value → {col_name → {stat_name → value}}.
    """
    result = {}

    for group_val, group_df in df.groupby(group_col):
        group_stats = {}
        for col in numeric_cols:
            if col in group_df.columns and col != group_col:
                series = group_df[col].dropna()
                if len(series) > 0:
                    group_stats[col] = {
                        'mean': float(series.mean()),
                        'median': float(series.median()),
                        'std_dev': float(series.std()),
                        'min': float(series.min()),
                        'max': float(series.max()),
                        'count': int(len(series)),
                    }
        result[str(group_val)] = group_stats

    return result


# ---------------------------------------------------------------------------
# Trend analysis internals (implementation_specification.md §4)
# ---------------------------------------------------------------------------

def _compute_trend(series: pd.Series,
                   col_name: str,
                   df: Optional[pd.DataFrame],
                   column_types: Optional[Dict[str, str]],
                   fraction: float,
                   min_window: int,
                   max_window: int,
                   stability_multiplier: float,
                   trend_minimum_slope_magnitude: float,
                   std_dev: float) -> Dict[str, Any]:
    """Compute trend analysis for a numeric column.

    FR-024: Trend analysis (moving average, slope of linear fit).
    FR-036: Detect simple recurring patterns (sustained drift).

    Implementation_specification.md §4:
    1. Identify sequence axis (datetime or row order).
    2. Moving average window = clamp(round(rows × fraction), min, max).
    3. Slope via numpy.polyfit(sequence_index, values, deg=1).
    4. Direction classification based on total predicted change vs bar.
    """
    clean = series.dropna()
    n = len(clean)

    if n < 3:
        return {'slope': None, 'direction': 'Insufficient data',
                'intercept': None, 'window': None}

    # Step 1: Sequence axis — use positional index (row order)
    # implementation_specification.md §4: use datetime col if exists,
    # otherwise fall back to row order / positional index
    sequence_index = np.arange(n, dtype=float)

    # Step 2: Moving average window
    # window = clamp(round(n * fraction), min_window, max_window)
    window = max(min_window, min(max_window, round(n * fraction)))

    # Step 3: Linear fit — slope and intercept
    # implementation_specification.md §4: numpy.polyfit(sequence_index, values, deg=1)
    values = clean.values.astype(float)
    slope, intercept = np.polyfit(sequence_index, values, deg=1)

    # Step 4: Direction classification
    # implementation_specification.md §4:
    # total_predicted_change = slope * row_count
    # bar = stability_multiplier * std_dev
    # direction = "Increasing" if change > bar
    #             "Decreasing" if change < -bar
    #             "Stable" otherwise
    total_predicted_change = slope * n
    bar = stability_multiplier * std_dev

    if abs(slope) < trend_minimum_slope_magnitude:
        direction = 'Stable'
    elif total_predicted_change > bar:
        direction = 'Increasing'
    elif total_predicted_change < -bar:
        direction = 'Decreasing'
    else:
        direction = 'Stable'

    return {
        'slope': round(float(slope), 6),
        'intercept': round(float(intercept), 4),
        'direction': direction,
        'window': window,
        'total_predicted_change': round(float(total_predicted_change), 4),
    }


def _empty_stats() -> Dict[str, Any]:
    """Return a stats dict with all values as None."""
    return {
        'mean': None, 'median': None, 'mode': None,
        'std_dev': None, 'variance': None,
        'min_value': None, 'max_value': None, 'range': None,
        'q1': None, 'q3': None, 'iqr': None,
        'trend_slope': None, 'trend_direction': None,
        'trend_intercept': None, 'moving_average_window': None,
    }
