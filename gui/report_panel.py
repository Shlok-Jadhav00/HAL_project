"""
AEIA — Report Panel (Module 10)

Provides report preview and export controls.

FRs implemented: FR-071 through FR-080.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/.
"""

import logging
from typing import Any, Dict

from PyQt5.QtWidgets import (
    QCheckBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from gui.theme import (
    MODULE_COLORS, MUTED_SLATE,
)

logger = logging.getLogger('aeia.report_panel')

# Error message from implementation_specification.md §9
ERROR_REPORT_SAVE = (
    "The report could not be saved to the selected location. "
    "Please check that the folder exists and that you have "
    "permission to write to it."
)


class ReportPanel(QWidget):
    """Report preview and export panel.

    FR-074: Preview report on-screen before exporting.
    FR-075: Choose save location and filename.
    FR-076: Re-export after editing notes without re-running analysis.
    FR-069: Toggle charts on/off per report.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis_results = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the report panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Module accent
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(
            f'background-color: {MODULE_COLORS["Report"]};'
        )
        layout.addWidget(accent)

        # Title
        title = QLabel('Report Export')
        title.setObjectName('pageTitle')
        layout.addWidget(title)

        # Options
        options = QGroupBox('Export Options')
        options_layout = QVBoxLayout(options)

        self.include_charts_cb = QCheckBox('Include charts/graphs (FR-069)')
        self.include_charts_cb.setChecked(True)
        options_layout.addWidget(self.include_charts_cb)

        layout.addWidget(options)

        # Preview (FR-074)
        preview_group = QGroupBox('Report Preview')
        preview_layout = QVBoxLayout(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText(
            'Run analysis first to preview the report...'
        )
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group, 1)

        # Export buttons
        btn_layout = QHBoxLayout()

        self.export_pdf_btn = QPushButton('📄  Export PDF')
        self.export_pdf_btn.setFixedHeight(40)
        self.export_pdf_btn.clicked.connect(lambda: self._export('pdf'))
        btn_layout.addWidget(self.export_pdf_btn)

        self.export_csv_btn = QPushButton('📊  Export CSV')
        self.export_csv_btn.setFixedHeight(40)
        self.export_csv_btn.setStyleSheet(
            f'background-color: {MUTED_SLATE};'
        )
        self.export_csv_btn.clicked.connect(lambda: self._export('csv'))
        btn_layout.addWidget(self.export_csv_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def set_results(self, results: Dict[str, Any]):
        """Set analysis results and update preview."""
        self.analysis_results = results
        self._update_preview()

    def _update_preview(self):
        """Update the report preview text (FR-074)."""
        if not self.analysis_results:
            return

        r = self.analysis_results
        lines = []

        lines.append('<h2>AEIA Engineering Analysis Report</h2>')
        lines.append(f'<p><b>Dataset:</b> {r.get("dataset_info", {}).get("filename", "N/A")}</p>')

        # Summary
        insights = r.get('insights', {})
        lines.append(f'<p>{insights.get("dataset_summary", "")}</p>')

        # Conclusion
        lines.append(f'<h3>Conclusion</h3>')
        lines.append(f'<p>{r.get("conclusion", "")}</p>')

        # Recommendations
        recs = r.get('recommendations', [])
        if recs:
            lines.append('<h3>Recommendations</h3>')
            for i, rec in enumerate(recs, 1):
                lines.append(f'<p>{i}. {rec.get("text", "")}</p>')

        # Findings count
        all_insights = insights.get('all_insights', [])
        lines.append(f'<p><i>{len(all_insights)} total findings</i></p>')

        self.preview_text.setHtml(''.join(lines))

    def _export(self, fmt: str):
        """Export the report (FR-075)."""
        if not self.analysis_results:
            QMessageBox.information(
                self, 'No Results',
                'Please run analysis before exporting a report.'
            )
            return

        from core.report_builder import (
            generate_pdf_report, generate_csv_export,
            generate_report_filename,
        )

        dataset_name = self.analysis_results.get(
            'dataset_info', {}
        ).get('filename', 'report')
        session_id = 1  # Will be set from session context

        import sys
        import os
        from pathlib import Path
        
        # Determine base directory (next to .exe when packaged, or project root in dev)
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
            
        reports_dir = base_dir / 'reports'
        try:
            reports_dir.mkdir(exist_ok=True)
        except OSError:
            pass # Fall back to current directory if permissions fail
            
        default_name = generate_report_filename(dataset_name, session_id, fmt)
        default_path = str(reports_dir / default_name) if reports_dir.exists() else default_name

        if fmt == 'pdf':
            file_filter = 'PDF Files (*.pdf);;All Files (*)'
        else:
            file_filter = 'CSV Files (*.csv);;All Files (*)'

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Report', default_path, file_filter
        )

        if not file_path:
            return

        try:
            r = self.analysis_results
            if fmt == 'pdf':
                chart_bytes = {}
                if self.include_charts_cb.isChecked():
                    chart_bytes = r.get('chart_bytes', {})

                generate_pdf_report(
                    file_path, r['dataset_info'], session_id,
                    r['statistics'], r['anomalies'], r['insights'],
                    r['conclusion'], r['recommendations'],
                    charts=chart_bytes,
                    include_charts=self.include_charts_cb.isChecked(),
                )
            else:
                generate_csv_export(
                    file_path, r['statistics'], r['anomalies'],
                )

            QMessageBox.information(
                self, 'Export Complete',
                f'Report saved to:\n{file_path}'
            )

        except Exception as exc:
            logger.error('Export failed: %s', exc, exc_info=True)
            QMessageBox.critical(self, 'Export Failed', ERROR_REPORT_SAVE)
