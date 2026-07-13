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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_trend_chart(df: pd.DataFrame,
                         column: str,
                         statistics: Dict[str, Any],
                         anomalies: Optional[Dict[str, Any]] = None,
                         figsize: Tuple[float, float] = (10, 4),
                         ) -> plt.Figure:
    """Generate a line/trend chart for an ordered numeric column.

    FR-066: Line/trend chart with anomalies highlighted.
    color_philosophy.md §4: Base line in Signal Blue, anomaly markers
    in Alert Red.

    Args:
        df: The cleaned DataFrame.
        column: The column to plot.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        figsize: Figure dimensions.

    Returns:
        matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor=PANEL_WHITE)
    ax.set_facecolor(CONSOLE_GREY)

    series = df[column].dropna()
    x = np.arange(len(series))
    y = series.values

    # Main data line (Signal Blue)
    ax.plot(x, y, color=SIGNAL_BLUE, linewidth=1.5, label=column, zorder=2)

    # Moving average overlay if available
    col_stats = statistics.get('per_column', {}).get(column, {})
    window = col_stats.get('moving_average_window')
    if window and window > 1 and len(y) >= window:
        ma = pd.Series(y).rolling(window=window, center=True).mean()
        ax.plot(x, ma.values, color=INSTRUMENT_NAVY, linewidth=1.0,
                linestyle='--', alpha=0.7, label=f'Moving Avg (w={window})',
                zorder=2)

    # Trend line overlay
    slope = col_stats.get('trend_slope')
    intercept = col_stats.get('trend_intercept')
    if slope is not None and intercept is not None:
        trend_y = slope * x + intercept
        ax.plot(x, trend_y, color=MUTED_SLATE, linewidth=1.0,
                linestyle=':', alpha=0.8,
                label=f'Trend (slope={slope:.4f})', zorder=2)

    # Highlight anomaly points (Alert Red markers per color_philosophy.md §4)
    if anomalies:
        anomaly_rows = _get_anomaly_rows_for_column(anomalies, column, df)
        if anomaly_rows:
            ax_indices = []
            ax_values = []
            for row_idx in anomaly_rows:
                if row_idx in series.index:
                    pos = list(series.index).index(row_idx)
                    ax_indices.append(pos)
                    ax_values.append(series.at[row_idx])
            if ax_indices:
                ax.scatter(ax_indices, ax_values, color=ALERT_RED,
                           s=60, zorder=5, label='Anomaly',
                           edgecolors=GRAPHITE, linewidths=0.5)

    # Styling
    ax.set_title(f'Trend: {column}', fontsize=12, fontweight='bold',
                 color=GRAPHITE)
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
                        ) -> Dict[str, bytes]:
    """Generate all chart types for the dataset.

    FR-069: Charts are toggle-able per report — this function generates
    all of them; the caller decides which to include.

    Args:
        df: The cleaned DataFrame.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        column_types: Dict mapping column name → type string.

    Returns:
        Dict mapping chart_name → Figure.
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
            fig = generate_trend_chart(df, col, statistics, anomalies)
            if fig is not None:
                charts[f'trend_{col}'] = save_figure_to_bytes(fig)
        except Exception as exc:
            logger.warning('Failed to generate trend chart for %s: %s',
                           col, exc)

    # FR-067: Histograms for each numeric column
    for col in numeric_cols:
        try:
            fig = generate_histogram(df, col)
            if fig is not None:
                charts[f'histogram_{col}'] = save_figure_to_bytes(fig)
        except Exception as exc:
            logger.warning('Failed to generate histogram for %s: %s',
                           col, exc)

    # FR-068: Correlation heatmap
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
