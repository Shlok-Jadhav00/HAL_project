"""
AEIA — Visualization Module (Module 8)

Generates Matplotlib charts for trend lines, histograms, and correlation
heatmaps. All charts generated locally — no external charting service (FR-070).

FRs implemented: FR-066 through FR-070.
Chart colors: color_philosophy.md §4 (Charts).
Algorithm reference: implementation_specification.md §4.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for offline use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger('aeia.chart_builder')


# ---------------------------------------------------------------------------
# Color constants from color_philosophy.md
# ---------------------------------------------------------------------------

INSTRUMENT_NAVY = '#10243E'
SIGNAL_BLUE = '#2563EB'
ALERT_RED = '#DC2626'
CAUTION_AMBER = '#D97706'
CONSOLE_GREY = '#F7F8FA'
PANEL_WHITE = '#FFFFFF'
STEEL_LINE = '#D3D8E0'
GRAPHITE = '#111827'
MUTED_SLATE = '#6B7280'
CONFIRMED_GREEN = '#16A34A'

# Severity → marker color (color_philosophy.md §Severity Color Mapping)
SEVERITY_COLORS = {
    'Critical': ALERT_RED,
    'Warning': CAUTION_AMBER,
    'Info': SIGNAL_BLUE,
}

# Default chart settings — overridden by config/settings.json at runtime
_DEFAULT_CHART_CFG = {
    'large_dataset_threshold': 5000,
    'full_resolution_max_width_px': 20000,
    'downsampling_points_per_pixel': 2,
    'downsampling_max_points': 5000,
    'downsampling_min_points': 500,
}


def _load_chart_config() -> Dict[str, Any]:
    """Load chart configuration from settings.json, with defaults."""
    try:
        from core.config_manager import load_settings
        settings = load_settings()
        cfg = settings.get('charts', {})
        merged = dict(_DEFAULT_CHART_CFG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(_DEFAULT_CHART_CFG)


# ---------------------------------------------------------------------------
# Downsampling helpers (optimised for CPU-only HAL PCs)
# ---------------------------------------------------------------------------

def _minmax_downsample(x: np.ndarray, y: np.ndarray,
                       n_buckets: int) -> Tuple[np.ndarray, np.ndarray]:
    """Min/Max bucket downsampling — O(n), pure NumPy.

    Splits the series into n_buckets segments. For each bucket, keeps the
    min and max values (preserving spikes and dips). Returns ~2*n_buckets points.
    Used for datasets between 5,000–20,000 rows.
    """
    n = len(x)
    if n <= n_buckets * 2:
        return x, y

    bucket_size = n / n_buckets
    x_out = []
    y_out = []

    for i in range(n_buckets):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        end = min(end, n)
        if start >= end:
            continue

        bucket_y = y[start:end]
        min_idx = start + int(np.argmin(bucket_y))
        max_idx = start + int(np.argmax(bucket_y))

        # Add min and max in order of their position
        if min_idx <= max_idx:
            x_out.extend([x[min_idx], x[max_idx]])
            y_out.extend([y[min_idx], y[max_idx]])
        else:
            x_out.extend([x[max_idx], x[min_idx]])
            y_out.extend([y[max_idx], y[min_idx]])

    return np.array(x_out), np.array(y_out)


def _lttb_downsample(x: np.ndarray, y: np.ndarray,
                     target_points: int) -> Tuple[np.ndarray, np.ndarray]:
    """Largest Triangle Three Bucket (LTTB) downsampling — O(n), pure NumPy.

    Selects the most visually significant point per bucket based on
    triangle area maximisation. Used for datasets > 20,000 rows.
    """
    n = len(x)
    if n <= target_points:
        return x, y

    # Always keep first and last
    sampled_indices = [0]

    bucket_size = (n - 2) / (target_points - 2)

    a_idx = 0  # Previously selected point

    for i in range(1, target_points - 1):
        # Calculate bucket boundaries
        avg_start = int((i + 0) * bucket_size) + 1
        avg_end = int((i + 1) * bucket_size) + 1
        avg_end = min(avg_end, n)

        # Average of next bucket (for triangle calculation)
        next_start = int((i + 1) * bucket_size) + 1
        next_end = int((i + 2) * bucket_size) + 1
        next_end = min(next_end, n)

        if next_start >= n:
            next_start = n - 1
        if next_end > n:
            next_end = n

        avg_x = np.mean(x[next_start:next_end]) if next_start < next_end else x[-1]
        avg_y = np.mean(y[next_start:next_end]) if next_start < next_end else y[-1]

        # Find point in current bucket that forms the largest triangle
        max_area = -1.0
        max_idx = avg_start

        a_x = x[a_idx]
        a_y = y[a_idx]

        for j in range(avg_start, min(avg_end, n)):
            # Triangle area (simplified — proportional is sufficient)
            area = abs(
                (a_x - avg_x) * (y[j] - a_y) -
                (a_x - x[j]) * (avg_y - a_y)
            )
            if area > max_area:
                max_area = area
                max_idx = j

        sampled_indices.append(max_idx)
        a_idx = max_idx

    sampled_indices.append(n - 1)
    idx = np.array(sampled_indices)
    return x[idx], y[idx]


def _compute_target_points(series_length: int,
                           chart_width_inches: float = 10.0,
                           dpi: int = 150,
                           cfg: Optional[Dict] = None) -> int:
    """Calculate adaptive point count based on chart pixel width.

    target = chart_width_px * points_per_pixel, clamped to [min, max].
    """
    if cfg is None:
        cfg = _load_chart_config()

    chart_width_px = chart_width_inches * dpi
    points_per_pixel = cfg.get('downsampling_points_per_pixel', 2)
    target = int(chart_width_px * points_per_pixel)
    target = min(target, cfg.get('downsampling_max_points', 5000))
    target = max(target, cfg.get('downsampling_min_points', 500))
    # Never upsample
    target = min(target, series_length)
    return target


def _downsample_for_chart(x: np.ndarray, y: np.ndarray,
                          chart_width_inches: float = 10.0,
                          anomaly_positions: Optional[List[int]] = None,
                          cfg: Optional[Dict] = None,
                          ) -> Tuple[np.ndarray, np.ndarray, Optional[str]]:
    """Orchestrator: pick strategy, downsample, and force-keep anomaly points.

    Tiered strategy:
      < 5,000 rows  → No downsampling.
      5k–20k rows   → MinMax bucket downsampling.
      > 20k rows    → LTTB downsampling.

    After downsampling, any anomaly positions not already present are
    force-inserted and the arrays are re-sorted by x.

    Returns:
        (x_down, y_down, subtitle_text)
        subtitle_text is None if no downsampling occurred.
    """
    if cfg is None:
        cfg = _load_chart_config()

    n = len(x)
    threshold = cfg.get('large_dataset_threshold', 5000)

    if n <= threshold:
        return x, y, None

    target = _compute_target_points(n, chart_width_inches, cfg=cfg)

    if n <= 20000:
        n_buckets = target // 2  # MinMax produces ~2 points per bucket
        n_buckets = max(n_buckets, 100)
        x_d, y_d = _minmax_downsample(x, y, n_buckets)
        method = 'min/max'
    else:
        x_d, y_d = _lttb_downsample(x, y, target)
        method = 'LTTB'

    # Force-insert anomaly positions so they are never lost
    if anomaly_positions:
        kept_x_set = set(x_d.tolist())
        extra_x = []
        extra_y = []
        for pos in anomaly_positions:
            if 0 <= pos < n and pos not in kept_x_set:
                extra_x.append(x[pos])
                extra_y.append(y[pos])
        if extra_x:
            x_d = np.concatenate([x_d, np.array(extra_x)])
            y_d = np.concatenate([y_d, np.array(extra_y)])
            sort_idx = np.argsort(x_d)
            x_d = x_d[sort_idx]
            y_d = y_d[sort_idx]

    subtitle = (
        f"Overview of {n:,}-row dataset "
        f"({method} downsampled to {len(x_d):,} points)"
    )
    logger.info('Downsampled %s: %d → %d points via %s', subtitle, n, len(x_d), method)
    return x_d, y_d, subtitle

def generate_trend_chart(df: pd.DataFrame,
                         column: str,
                         statistics: Dict[str, Any],
                         anomalies: Optional[Dict[str, Any]] = None,
                         figsize: Tuple[float, float] = (10, 4),
                         chart_mode: str = 'auto',
                         row_start: Optional[int] = None,
                         row_end: Optional[int] = None,
                         ) -> plt.Figure:
    """Generate a line/trend chart for an ordered numeric column.

    FR-066: Line/trend chart with anomalies highlighted.
    color_philosophy.md §4: Base line in Signal Blue, anomaly markers
    in Alert Red.

    Supports adaptive rendering for large datasets:
      - 'auto':     Adaptive downsampling if > threshold, else raw plot.
      - 'overview': Always downsample (fast & recommended).
      - 'full':     Plot all points on a wide, scrollable canvas.
      - 'range':    Plot only rows [row_start:row_end].

    Args:
        df: The cleaned DataFrame.
        column: The column to plot.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        figsize: Base figure dimensions.
        chart_mode: 'auto', 'overview', 'full', or 'range'.
        row_start: Start row for 'range' mode (0-based index).
        row_end: End row for 'range' mode (0-based, exclusive).

    Returns:
        matplotlib Figure object.
    """
    cfg = _load_chart_config()

    # --- Slice for range mode ---
    if chart_mode == 'range' and row_start is not None and row_end is not None:
        df = df.iloc[row_start:row_end]

    series = df[column].dropna()
    n = len(series)
    if n == 0:
        fig, ax = plt.subplots(figsize=figsize, facecolor=PANEL_WHITE)
        ax.text(0.5, 0.5, f'No data for {column}', transform=ax.transAxes,
                ha='center', va='center', color=MUTED_SLATE)
        return fig

    x_raw = np.arange(n)
    y_raw = series.values

    # --- Collect anomaly positions (as 0-based plot indices) ---
    anomaly_plot_positions = []
    anomaly_plot_values = []
    if anomalies:
        anomaly_rows = _get_anomaly_rows_for_column(anomalies, column, df)
        for row_idx in anomaly_rows:
            if row_idx in series.index:
                pos = list(series.index).index(row_idx)
                anomaly_plot_positions.append(pos)
                anomaly_plot_values.append(series.at[row_idx])

    # --- Determine effective mode ---
    effective_mode = chart_mode
    if effective_mode == 'auto':
        threshold = cfg.get('large_dataset_threshold', 5000)
        effective_mode = 'overview' if n > threshold else 'raw'

    # --- Compute figure size and data arrays based on mode ---
    subtitle = None

    if effective_mode == 'overview':
        # Downsample with anomaly preservation
        x_plot, y_plot, subtitle = _downsample_for_chart(
            x_raw, y_raw,
            chart_width_inches=figsize[0],
            anomaly_positions=anomaly_plot_positions,
            cfg=cfg,
        )
        current_figsize = figsize

    elif effective_mode == 'full':
        # Wide canvas capped at max_width_px
        max_px = cfg.get('full_resolution_max_width_px', 20000)
        dpi = 150
        max_width_inches = max_px / dpi
        dynamic_width = min(max(figsize[0], n / 100.0), max_width_inches)
        current_figsize = (dynamic_width, figsize[1])
        x_plot, y_plot = x_raw, y_raw

    elif effective_mode == 'range':
        current_figsize = figsize
        x_plot, y_plot = x_raw, y_raw

    else:
        # 'raw' — small dataset, no downsampling, mild dynamic width
        dynamic_width = max(figsize[0], min(n / 50.0, 50.0))
        current_figsize = (dynamic_width, figsize[1])
        x_plot, y_plot = x_raw, y_raw

    # --- Create figure ---
    fig, ax = plt.subplots(figsize=current_figsize, facecolor=PANEL_WHITE)
    ax.set_facecolor(CONSOLE_GREY)

    # Main data line (Signal Blue)
    lw = 1.5 if n < 10000 else 0.8  # Thinner line for dense plots
    ax.plot(x_plot, y_plot, color=SIGNAL_BLUE, linewidth=lw,
            label=column, zorder=2)

    # Moving average overlay (only for non-downsampled modes)
    if effective_mode in ('raw', 'full', 'range'):
        col_stats = statistics.get('per_column', {}).get(column, {})
        window = col_stats.get('moving_average_window')
        if window and window > 1 and len(y_plot) >= window:
            ma = pd.Series(y_plot).rolling(window=window, center=True).mean()
            ax.plot(x_plot, ma.values, color=INSTRUMENT_NAVY, linewidth=1.0,
                    linestyle='--', alpha=0.7, label=f'Moving Avg (w={window})',
                    zorder=2)

    # Trend line overlay (works in all modes using the full x_raw range)
    col_stats = statistics.get('per_column', {}).get(column, {})
    slope = col_stats.get('trend_slope')
    intercept = col_stats.get('trend_intercept')
    if slope is not None and intercept is not None:
        trend_y = slope * x_plot + intercept
        ax.plot(x_plot, trend_y, color=MUTED_SLATE, linewidth=1.0,
                linestyle=':', alpha=0.8,
                label=f'Trend (slope={slope:.4f})', zorder=2)

    # Highlight anomaly points (Alert Red markers per color_philosophy.md §4)
    # In overview mode, anomaly positions were force-inserted into the
    # downsampled data, so we overlay them from the original positions.
    if anomaly_plot_positions:
        ax.scatter(anomaly_plot_positions, anomaly_plot_values,
                   color=ALERT_RED, s=60, zorder=5, label='Anomaly',
                   edgecolors=GRAPHITE, linewidths=0.5)

    # --- Titles and styling ---
    if effective_mode == 'range' and row_start is not None:
        title = f'Trend: {column} (Rows {row_start + 1:,}–{row_end:,})'
    else:
        title = f'Trend: {column}'
    ax.set_title(title, fontsize=12, fontweight='bold', color=GRAPHITE)

    if subtitle:
        ax.text(0.5, 1.01, subtitle, transform=ax.transAxes,
                fontsize=8, color=MUTED_SLATE, ha='center', va='bottom',
                style='italic')

    ax.set_xlabel('Sample Index', fontsize=10, color=GRAPHITE)
    ax.set_ylabel(column, fontsize=10, color=GRAPHITE)
    ax.legend(fontsize=8, loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3, color=STEEL_LINE)
    ax.tick_params(colors=GRAPHITE, labelsize=8)

    for spine in ax.spines.values():
        spine.set_color(STEEL_LINE)

    fig.tight_layout()
    return fig


def generate_histogram(df: pd.DataFrame,
                       column: str,
                       bins: int = 30,
                       figsize: Tuple[float, float] = (8, 4),
                       ) -> plt.Figure:
    """Generate a histogram/distribution chart for a numeric column.

    FR-067: Histogram/distribution chart for any selected numeric column.

    Args:
        df: The cleaned DataFrame.
        column: The column to plot.
        bins: Number of histogram bins.
        figsize: Figure dimensions.

    Returns:
        matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor=PANEL_WHITE)
    ax.set_facecolor(CONSOLE_GREY)

    series = df[column].dropna()

    ax.hist(series.values, bins=bins, color=SIGNAL_BLUE, alpha=0.8,
            edgecolor=INSTRUMENT_NAVY, linewidth=0.5)

    # Add mean and median lines
    mean_val = series.mean()
    median_val = series.median()
    ax.axvline(mean_val, color=ALERT_RED, linestyle='--', linewidth=1.2,
               label=f'Mean: {mean_val:.2f}')
    ax.axvline(median_val, color=CONFIRMED_GREEN, linestyle='-.',
               linewidth=1.2, label=f'Median: {median_val:.2f}')

    # Styling
    ax.set_title(f'Distribution: {column}', fontsize=12, fontweight='bold',
                 color=GRAPHITE)
    ax.set_xlabel(column, fontsize=10, color=GRAPHITE)
    ax.set_ylabel('Frequency', fontsize=10, color=GRAPHITE)
    ax.legend(fontsize=8, loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3, color=STEEL_LINE, axis='y')
    ax.tick_params(colors=GRAPHITE, labelsize=8)

    for spine in ax.spines.values():
        spine.set_color(STEEL_LINE)

    fig.tight_layout()
    return fig


def generate_correlation_heatmap(statistics: Dict[str, Any],
                                  figsize: Tuple[float, float] = (8, 6),
                                  ) -> Optional[plt.Figure]:
    """Generate a correlation heatmap for numeric columns.

    FR-068: Correlation heatmap for numeric columns.

    Args:
        statistics: Output of statistics_engine.compute_statistics().
        figsize: Figure dimensions.

    Returns:
        matplotlib Figure object, or None if no correlation data.
    """
    corr_data = statistics.get('correlations', {})
    matrix = corr_data.get('matrix')

    if matrix is None or not isinstance(matrix, dict):
        logger.info('No correlation matrix available for heatmap.')
        return None

    # Convert dict-of-dicts to DataFrame
    if isinstance(matrix, dict):
        corr_df = pd.DataFrame(matrix)
    else:
        corr_df = matrix

    if corr_df.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize, facecolor=PANEL_WHITE)

    # Create heatmap
    im = ax.imshow(corr_df.values, cmap='RdBu_r', vmin=-1, vmax=1,
                   aspect='auto')

    # Set tick labels
    cols = list(corr_df.columns)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, fontsize=8, rotation=45, ha='right',
                       color=GRAPHITE)
    ax.set_yticklabels(cols, fontsize=8, color=GRAPHITE)

    # Add correlation values as text annotations
    for i in range(len(cols)):
        for j in range(len(cols)):
            val = corr_df.iloc[i, j]
            text_color = PANEL_WHITE if abs(val) > 0.5 else GRAPHITE
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=7, color=text_color)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=8, colors=GRAPHITE)

    ax.set_title('Correlation Heatmap', fontsize=12, fontweight='bold',
                 color=GRAPHITE)

    fig.tight_layout()
    return fig


def save_figure_to_bytes(fig: plt.Figure, dpi: int = 150,
                         fmt: str = 'png') -> bytes:
    """Save a matplotlib figure to bytes for embedding in reports.

    Args:
        fig: The figure to save.
        dpi: Resolution.
        fmt: Image format ('png', 'svg', etc.).

    Returns:
        Image data as bytes.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    buf.seek(0)
    data = buf.read()
    buf.close()
    plt.close(fig)
    return data


def save_figure_to_file(fig: plt.Figure, path: str, dpi: int = 150) -> str:
    """Save a matplotlib figure to a file.

    Args:
        fig: The figure to save.
        path: Output file path.
        dpi: Resolution.

    Returns:
        The saved file path.
    """
    fig.savefig(path, dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info('Saved chart to %s', path)
    return path


def generate_all_charts(df: pd.DataFrame,
                        statistics: Dict[str, Any],
                        anomalies: Dict[str, Any],
                        column_types: Dict[str, str],
                        chart_mode: str = 'auto',
                        row_start: Optional[int] = None,
                        row_end: Optional[int] = None,
                        ) -> Dict[str, bytes]:
    """Generate all chart types for the dataset.

    FR-069: Charts are toggle-able per report — this function generates
    all of them; the caller decides which to include.

    Args:
        df: The cleaned DataFrame.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        column_types: Dict mapping column name → type string.
        chart_mode: 'auto', 'overview', 'full', or 'range'.
        row_start: Start row for 'range' mode.
        row_end: End row for 'range' mode.

    Returns:
        Dict mapping chart_name → PNG bytes.
    """
    charts = {}

    numeric_cols = [
        col for col in df.columns
        if column_types.get(col) == 'numeric'
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    # FR-066: Trend charts for each numeric column
    for col in numeric_cols:
        try:
            fig = generate_trend_chart(
                df, col, statistics, anomalies,
                chart_mode=chart_mode,
                row_start=row_start,
                row_end=row_end,
            )
            if fig is not None:
                charts[f'trend_{col}'] = save_figure_to_bytes(fig)
        except Exception as exc:
            logger.warning('Failed to generate trend chart for %s: %s',
                           col, exc)

    # FR-067: Histograms for each numeric column (unaffected by chart_mode)
    for col in numeric_cols:
        try:
            fig = generate_histogram(df, col)
            if fig is not None:
                charts[f'histogram_{col}'] = save_figure_to_bytes(fig)
        except Exception as exc:
            logger.warning('Failed to generate histogram for %s: %s',
                           col, exc)

    # FR-068: Correlation heatmap (unaffected by chart_mode)
    try:
        fig = generate_correlation_heatmap(statistics)
        if fig is not None:
            charts['correlation_heatmap'] = save_figure_to_bytes(fig)
    except Exception as exc:
        logger.warning('Failed to generate correlation heatmap: %s', exc)

    logger.info('Generated %d charts.', len(charts))
    return charts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_anomaly_rows_for_column(anomalies: Dict[str, Any],
                                  column: str,
                                  df: pd.DataFrame) -> List[int]:
    """Get row indices for anomalies in a specific column."""
    rows = set()
    for a in anomalies.get('anomalies', []):
        a_col = a.get('column_name', '')
        # For single-column methods
        if a_col == column:
            rows.add(a.get('row_reference'))
        # For multivariate (IF), check if column is one of the involved ones
        elif ',' in a_col and column in a_col.split(','):
            rows.add(a.get('row_reference'))
    return sorted(r for r in rows if r is not None)
