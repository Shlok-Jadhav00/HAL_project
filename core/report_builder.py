"""
AEIA — Report Generation Module (Module 9)

Exports session results as PDF (via ReportLab) and CSV.
All generation is local — no internet-based rendering (FR-077).

FRs implemented: FR-071 through FR-080.
PDF layout: implementation_specification.md §8.
Colors: color_philosophy.md.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import csv
import io
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

from core import __version__

logger = logging.getLogger('aeia.report_builder')


# ---------------------------------------------------------------------------
# PDF layout constants (implementation_specification.md §8)
# ---------------------------------------------------------------------------

PAGE_SIZE = A4
MARGIN_CM = 2
MARGIN = MARGIN_CM * cm

# Font sizes (§8)
TITLE_FONT_SIZE = 22
SECTION_FONT_SIZE = 14
BODY_FONT_SIZE = 10
FOOTER_FONT_SIZE = 8

# Colors from color_philosophy.md
from core import color_palette as cp
INSTRUMENT_NAVY = colors.HexColor(cp.INSTRUMENT_NAVY)
SIGNAL_BLUE = colors.HexColor(cp.SIGNAL_BLUE)
ALERT_RED = colors.HexColor(cp.ALERT_RED)
CAUTION_AMBER = colors.HexColor(cp.CAUTION_AMBER)
INFO_BLUE = colors.HexColor(cp.INFO_BLUE)
GRAPHITE = colors.HexColor(cp.GRAPHITE)
STEEL_LINE = colors.HexColor(cp.STEEL_LINE)
CONSOLE_GREY = colors.HexColor(cp.CONSOLE_GREY)
PANEL_WHITE = colors.white

# Severity badge colors
SEVERITY_COLORS = {
    'Critical': ALERT_RED,
    'Warning': CAUTION_AMBER,
    'Info': INFO_BLUE,
}

# Disclaimer (implementation_specification.md §8)
DISCLAIMER_TEXT = (
    "This report was generated with AI-assisted analysis (AEIA). "
    "Findings and recommendations are advisory and require review and "
    "sign-off by a qualified engineer before any operational decision "
    "is made."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf_report(output_path: str,
                        dataset_info: Dict[str, Any],
                        session_id: int,
                        statistics: Dict[str, Any],
                        anomalies: Dict[str, Any],
                        insights: Dict[str, Any],
                        conclusion: str,
                        recommendations: List[Dict[str, Any]],
                        charts: Optional[Dict[str, bytes]] = None,
                        include_charts: bool = True,
                        ) -> str:
    """Generate a PDF report for the analysis session.

    FR-071: PDF containing Statistical Summary, Engineering Findings,
            Conclusion, Recommendations, and optional Graphs.
    FR-072: Header with dataset name, timestamp, and version.
    FR-073: Table of contents if 3+ sections.
    FR-077: Generated via ReportLab, no internet dependency.
    FR-079: Disclaimer footer on every page.

    Args:
        output_path: Where to save the PDF file.
        dataset_info: Dict with 'filename', 'row_count', 'column_count'.
        session_id: The session ID.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        insights: Output of insight_generator.generate_insights().
        conclusion: Output of recommendation_engine.generate_conclusion().
        recommendations: Output of recommendation_engine.generate_recommendations().
        charts: Optional dict mapping chart_name → PNG bytes data.
        include_charts: Whether to include charts (FR-069).

    Returns:
        The output file path.

    Raises:
        OSError: If the file cannot be written (FR-079 error message
                 is handled by the caller/GUI).
    """
    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 0.5 * cm,  # Extra space for footer
    )

    styles = _build_styles()
    story = []

    # 1. Cover / Header (FR-072)
    story.extend(_build_header(dataset_info, session_id, styles))

    # 2. Executive Summary (FR-059) - immediately after title page
    story.extend(_build_executive_summary_section(conclusion, styles))

    # Count sections for TOC decision (Executive Summary removed from TOC as it precedes it)
    sections = ['Statistical Summary', 'Engineering Findings', 'Recommendations']
    if include_charts and charts:
        sections.append('Graphs')

    # 3. Table of Contents (FR-073, only if 3+ sections)
    if len(sections) >= 3:
        story.extend(_build_toc(sections, styles))

    # 4. Statistical Summary
    story.extend(_build_statistical_summary(statistics, styles))

    # 5. Engineering Findings (FR-054, grouped by column)
    story.extend(_build_findings_section(insights, styles))

    # 6. Recommendations (FR-061, ranked)
    story.extend(_build_recommendations_section(recommendations, styles))

    # 7. Graphs (FR-069, optional)
    if include_charts and charts:
        story.extend(_build_charts_section(charts, styles))

    # Build the PDF with disclaimer footer on every page
    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)

    logger.info('PDF report generated: %s', output_path)
    return output_path


def generate_csv_export(output_path: str,
                        statistics: Dict[str, Any],
                        anomalies: Dict[str, Any],
                        ) -> str:
    """Export raw statistical results as CSV.

    FR-080: Support exporting raw statistical results additionally as CSV.

    Args:
        output_path: Where to save the CSV file.
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().

    Returns:
        The output file path.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Statistics sheet
        writer.writerow(['=== Statistical Summary ==='])
        writer.writerow(['Column', 'Mean', 'Median', 'Mode', 'Std Dev',
                          'Variance', 'Min', 'Max', 'Q1', 'Q3', 'IQR',
                          'Trend Slope', 'Trend Direction'])

        per_column = statistics.get('per_column', {})
        for col, s in per_column.items():
            writer.writerow([
                col,
                _fmt(s.get('mean')), _fmt(s.get('median')),
                _fmt(s.get('mode')), _fmt(s.get('std_dev')),
                _fmt(s.get('variance')), _fmt(s.get('min_value')),
                _fmt(s.get('max_value')), _fmt(s.get('q1')),
                _fmt(s.get('q3')), _fmt(s.get('iqr')),
                _fmt(s.get('trend_slope')),
                s.get('trend_direction', ''),
            ])

        writer.writerow([])

        # Anomalies sheet
        writer.writerow(['=== Anomalies ==='])
        writer.writerow(['Column', 'Row', 'Method', 'Severity', 'Value'])

        for a in anomalies.get('anomalies', []):
            writer.writerow([
                a.get('column_name', ''),
                a.get('row_reference', ''),
                a.get('method', ''),
                a.get('severity', ''),
                _fmt(a.get('value')),
            ])

        # Correlations
        strong_pairs = statistics.get('correlations', {}).get(
            'strong_pairs', []
        )
        if strong_pairs:
            writer.writerow([])
            writer.writerow(['=== Strong Correlations ==='])
            writer.writerow(['Column A', 'Column B', 'r-value'])
            for pair in strong_pairs:
                writer.writerow([
                    pair.get('column_a', ''),
                    pair.get('column_b', ''),
                    _fmt(pair.get('r_value')),
                ])

    logger.info('CSV export generated: %s', output_path)
    return output_path


def generate_report_filename(dataset_name: str,
                              session_id: int,
                              extension: str = 'pdf') -> str:
    """Generate the standardized report filename.

    implementation_specification.md §8:
    {dataset_name_sanitized}_{session_id}_{YYYYMMDD_HHMMSS}.{ext}

    Args:
        dataset_name: Original dataset filename (without extension).
        session_id: The session ID.
        extension: File extension ('pdf' or 'csv').

    Returns:
        The generated filename string.
    """
    # Sanitize: remove extension, replace non-alphanumeric with _
    name_no_ext = os.path.splitext(dataset_name)[0]
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', name_no_ext)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_str = f'S{session_id:05d}'

    return f'{sanitized}_{session_str}_{timestamp}.{extension}'


# ---------------------------------------------------------------------------
# PDF building helpers
# ---------------------------------------------------------------------------

def _build_styles() -> Dict[str, ParagraphStyle]:
    """Build the report paragraph styles per implementation_specification.md §8."""
    base = getSampleStyleSheet()

    return {
        'title': ParagraphStyle(
            'AEIATitle',
            parent=base['Title'],
            fontName='Helvetica-Bold',
            fontSize=TITLE_FONT_SIZE,
            textColor=INSTRUMENT_NAVY,
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        'section': ParagraphStyle(
            'AEIASection',
            parent=base['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=SECTION_FONT_SIZE,
            textColor=INSTRUMENT_NAVY,
            spaceBefore=18,
            spaceAfter=8,
        ),
        'body': ParagraphStyle(
            'AEIABody',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=BODY_FONT_SIZE,
            textColor=GRAPHITE,
            spaceBefore=4,
            spaceAfter=4,
            leading=14,
        ),
        'footer': ParagraphStyle(
            'AEIAFooter',
            parent=base['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=FOOTER_FONT_SIZE,
            textColor=GRAPHITE,
            alignment=TA_CENTER,
        ),
        'subtitle': ParagraphStyle(
            'AEIASubtitle',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=BODY_FONT_SIZE,
            textColor=GRAPHITE,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        'toc_entry': ParagraphStyle(
            'AEIATocEntry',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=BODY_FONT_SIZE,
            textColor=SIGNAL_BLUE,
            spaceBefore=4,
            spaceAfter=4,
            leftIndent=20,
        ),
    }


def _build_header(dataset_info: Dict[str, Any],
                   session_id: int,
                   styles: Dict[str, ParagraphStyle],
                   ) -> list:
    """Build the report cover/header section (FR-072)."""
    elements = []

    elements.append(Spacer(1, 2 * cm))
    elements.append(
        Paragraph('AEIA Engineering Analysis Report', styles['title'])
    )
    elements.append(Spacer(1, 0.5 * cm))

    filename = dataset_info.get('filename', 'unknown')
    row_count = dataset_info.get('row_count', 0)
    col_count = dataset_info.get('column_count', 0)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    subtitle_text = (
        f"Dataset: {filename}<br/>"
        f"Rows: {row_count} | Columns: {col_count}<br/>"
        f"Session ID: S{session_id:05d}<br/>"
        f"Generated: {timestamp}<br/>"
        f"AEIA Version: {__version__}"
    )
    elements.append(Paragraph(subtitle_text, styles['subtitle']))
    elements.append(Spacer(1, 1 * cm))

    return elements


def _build_toc(sections: List[str],
                styles: Dict[str, ParagraphStyle]) -> list:
    """Build a simple table of contents (FR-073)."""
    elements = []
    elements.append(Paragraph('Table of Contents', styles['section']))

    for i, section_name in enumerate(sections, 1):
        elements.append(
            Paragraph(f'{i}. {section_name}', styles['toc_entry'])
        )

    elements.append(Spacer(1, 1 * cm))
    return elements


def _build_statistical_summary(statistics: Dict[str, Any],
                                styles: Dict[str, ParagraphStyle],
                                ) -> list:
    """Build the Statistical Summary section."""
    elements = []
    elements.append(Paragraph('Statistical Summary', styles['section']))

    per_column = statistics.get('per_column', {})

    if not per_column:
        elements.append(
            Paragraph('No statistical data available.', styles['body'])
        )
        return elements

    # Build table
    header = ['Column', 'Mean', 'Std Dev', 'Min', 'Max',
              'Q1', 'Q3', 'Trend']
    rows = [header]

    for col, s in per_column.items():
        direction = s.get('trend_direction', 'N/A')
        rows.append([
            col,
            _fmt(s.get('mean')),
            _fmt(s.get('std_dev')),
            _fmt(s.get('min_value')),
            _fmt(s.get('max_value')),
            _fmt(s.get('q1')),
            _fmt(s.get('q3')),
            direction,
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(_stats_table_style(len(rows)))
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    return elements


def _build_findings_section(insights: Dict[str, Any],
                             styles: Dict[str, ParagraphStyle]) -> list:
    """Build the Engineering Findings section (FR-054, grouped by column)."""
    elements = []
    elements.append(Paragraph('Engineering Findings', styles['section']))

    grouped = insights.get('grouped_by_column', {})

    if not grouped:
        elements.append(
            Paragraph('No findings to report.', styles['body'])
        )
        return elements

    for column, findings in grouped.items():
        # Column sub-header
        elements.append(
            Paragraph(f'<b>{column}</b>', styles['body'])
        )

        for finding in findings:
            severity = finding.get('severity', 'Info')
            sev_color = {
                'Critical': 'red',
                'Warning': '#D97706',
                'Info': '#1D4ED8',
            }.get(severity, 'black')

            text = finding.get('text', '')
            # Escape XML special chars for ReportLab
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            line = (
                f'<font color="{sev_color}">[{severity}]</font> '
                f'{text}'
            )
            elements.append(Paragraph(line, styles['body']))

        elements.append(Spacer(1, 0.3 * cm))

    return elements


def _build_executive_summary_section(conclusion: str,
                                       styles: Dict[str, ParagraphStyle]) -> list:
    """Build the Executive Summary section (FR-059)."""
    elements = []
    elements.append(Paragraph('Executive Summary', styles['section']))
    # Escape XML special chars
    safe_conclusion = conclusion.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Handle newlines
    safe_conclusion = safe_conclusion.replace('\n\n', '<br/><br/>').replace('\n', '<br/>')
    elements.append(Paragraph(safe_conclusion, styles['body']))
    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_recommendations_section(recommendations: List[Dict[str, Any]],
                                    styles: Dict[str, ParagraphStyle],
                                    ) -> list:
    """Build the Recommendations section (FR-061, ranked Critical→Warning→Info)."""
    elements = []
    elements.append(Paragraph('Recommendations', styles['section']))

    if not recommendations:
        elements.append(
            Paragraph('No recommendations to report.', styles['body'])
        )
        return elements

    for i, rec in enumerate(recommendations, 1):
        severity = rec.get('severity', 'Info')
        sev_color = {
            'Critical': 'red',
            'Warning': '#D97706',
            'Info': '#1D4ED8',
        }.get(severity, 'black')

        text = rec.get('text', '')
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        note = rec.get('engineer_note', '')

        line = (
            f'{i}. <font color="{sev_color}">[{severity}]</font> '
            f'{text}'
        )
        if note:
            note = note.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            line += f'<br/><i>Engineer note: {note}</i>'

        elements.append(Paragraph(line, styles['body']))

    elements.append(Spacer(1, 0.5 * cm))
    return elements


def _build_charts_section(charts: Dict[str, bytes],
                           styles: Dict[str, ParagraphStyle]) -> list:
    """Build the Graphs section (FR-069)."""
    elements = []
    elements.append(Paragraph('Graphs', styles['section']))

    for chart_name, chart_data in charts.items():
        # Convert chart_name to readable title
        readable = chart_name.replace('_', ' ').title()
        elements.append(Paragraph(f'<b>{readable}</b>', styles['body']))

        # Create image from bytes
        img_buf = io.BytesIO(chart_data)
        # Scale to fit page width
        page_width = A4[0] - 2 * MARGIN
        img = Image(img_buf, width=page_width, height=page_width * 0.4)
        elements.append(img)
        elements.append(Spacer(1, 0.5 * cm))

    return elements


def _draw_footer(canvas, doc):
    """Draw the disclaimer footer on every page (FR-079)."""
    canvas.saveState()
    canvas.setFont('Helvetica-Oblique', FOOTER_FONT_SIZE)
    canvas.setFillColor(GRAPHITE)

    # Footer text
    footer_y = MARGIN - 0.3 * cm
    page_width = A4[0]

    # Split disclaimer into lines that fit
    max_width = page_width - 2 * MARGIN
    canvas.setFont('Helvetica-Oblique', FOOTER_FONT_SIZE)

    # Simple wrapping
    words = DISCLAIMER_TEXT.split()
    lines = []
    current = []
    for word in words:
        test_line = ' '.join(current + [word])
        if canvas.stringWidth(test_line, 'Helvetica-Oblique',
                              FOOTER_FONT_SIZE) < max_width:
            current.append(word)
        else:
            lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))

    y = footer_y
    for line in reversed(lines):
        canvas.drawCentredString(page_width / 2, y, line)
        y -= FOOTER_FONT_SIZE + 2

    # Page number
    canvas.setFont('Helvetica', FOOTER_FONT_SIZE)
    canvas.drawRightString(
        page_width - MARGIN,
        MARGIN - 0.3 * cm - (len(lines)) * (FOOTER_FONT_SIZE + 2),
        f'Page {canvas.getPageNumber()}'
    )

    canvas.restoreState()


def _stats_table_style(num_rows: int) -> TableStyle:
    """Build a styled table for the statistical summary."""
    return TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), INSTRUMENT_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, STEEL_LINE),
        ('LINEBELOW', (0, 0), (-1, 0), 1, INSTRUMENT_NAVY),

        # Alternate row shading
        *[('BACKGROUND', (0, i), (-1, i), CONSOLE_GREY)
          for i in range(2, num_rows, 2)],

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(value, decimals: int = 4) -> str:
    """Format a numeric value for display."""
    if value is None:
        return 'N/A'
    try:
        return f'{float(value):.{decimals}f}'
    except (TypeError, ValueError):
        return str(value)
