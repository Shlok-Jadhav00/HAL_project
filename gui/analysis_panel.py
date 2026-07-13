"""
AEIA — Analysis Panel (Module 10)

Displays analysis results: statistics, anomalies, expert-system findings,
insights, conclusion, and recommendations. Allows false-positive marking
and regeneration.

FRs implemented: FR-021 through FR-040, FR-039, FR-057, FR-062, FR-065.
Layout: implementation_specification.md §7.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/.
"""

import logging
from typing import Any, Dict, List, Set, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from gui.theme import (
    GRAPHITE, MODULE_COLORS, MUTED_SLATE, PANEL_WHITE,
    SEVERITY_BG_COLORS, SEVERITY_COLORS,
)
from gui.report_panel import ReportPanel

logger = logging.getLogger('aeia.analysis_panel')


class AnalysisWorker(QThread):
    """Background thread for running the full analysis pipeline (FR-088)."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, session_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.session_data = session_data

    def run(self):
        try:
            from core.preprocessor import preprocess_dataset
            from core.statistics_engine import compute_statistics
            from core.anomaly_detector import detect_anomalies
            from core.expert_system import load_rules, evaluate_rules
            from core.insight_generator import generate_insights
            from core.recommendation_engine import (
                generate_conclusion, generate_recommendations,
            )
            from core.chart_builder import generate_all_charts


            from core.config_manager import load_settings, get_rules_path
            settings = load_settings()
            det_cfg = settings.get('detection', {})
            stat_cfg = settings.get('statistics', {})

            df = self.session_data['dataframe']
            col_types = self.session_data['column_types']

            self.progress.emit(10, 'Preprocessing...')
            df_clean, preprocess_log = preprocess_dataset(df, col_types)

            self.progress.emit(30, 'Computing statistics...')
            measurement_types = {
                k: v for k, v in col_types.items()
                if k != 'Sample_ID'
            }
            stats = compute_statistics(
                df_clean, measurement_types,
                correlation_threshold=stat_cfg.get('correlation_threshold', 0.7),
                trend_window_fraction=stat_cfg.get('trend_window_fraction_of_dataset', 0.1),
                trend_window_min=stat_cfg.get('trend_window_min_samples', 3),
                trend_window_max=stat_cfg.get('trend_window_max_samples', 20),
                trend_stability_multiplier=stat_cfg.get('trend_stability_std_multiplier', 0.5),
                trend_minimum_slope_magnitude=stat_cfg.get('trend_minimum_slope_magnitude', 0.01)
            )

            self.progress.emit(50, 'Detecting anomalies...')
            anomalies = detect_anomalies(
                df_clean, measurement_types,
                zscore_threshold=det_cfg.get('zscore_threshold', 3.0),
                iqr_multiplier=det_cfg.get('iqr_multiplier', 1.5),
                if_contamination=det_cfg.get('isolation_forest_contamination', 0.05),
                if_n_estimators=det_cfg.get('isolation_forest_n_estimators', 100),
                if_random_state=det_cfg.get('isolation_forest_random_state', 42)
            )

            self.progress.emit(65, 'Evaluating rules...')
            rules_path = get_rules_path()
            rules = load_rules(rules_path)
            matches = evaluate_rules(rules, stats, anomalies, df=df_clean)

            self.progress.emit(80, 'Generating insights...')
            dataset_info = self.session_data.get('dataset_info', {})
            insights = generate_insights(
                stats, anomalies, matches, dataset_info
            )

            self.progress.emit(90, 'Building conclusion...')
            conclusion = generate_conclusion(insights)
            recs = generate_recommendations(insights, matches)

            self.progress.emit(95, 'Generating graphs...')
            chart_bytes = generate_all_charts(df_clean, stats, anomalies, measurement_types)

            self.progress.emit(100, 'Analysis complete.')

            self.finished.emit({
                'dataframe': df_clean,
                'column_types': col_types,
                'measurement_types': measurement_types,
                'preprocess_log': preprocess_log,
                'statistics': stats,
                'anomalies': anomalies,
                'rules': rules,
                'rule_matches': matches,
                'insights': insights,
                'conclusion': conclusion,
                'recommendations': recs,
                'dataset_info': dataset_info,
                'chart_bytes': chart_bytes,
            })

        except Exception as exc:
            logger.error('Analysis failed: %s', exc, exc_info=True)
            self.error.emit(str(exc))


class AnalysisPanel(QWidget):
    """Analysis results display panel.

    FR-030: Statistical results in a sortable tab.
    FR-035: List detected anomalies with row reference, column, method.
    FR-039: Allow marking false positives.
    FR-054: Grouped Engineering Findings.
    FR-065: Conclusions/recommendations reviewable and editable.
    """

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.session_data = None
        self.analysis_results = None
        self.excluded_anomalies: Set[Tuple[str, int]] = set()
        self._worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the analysis panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Module accent
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(
            f'background-color: {MODULE_COLORS["Anomaly"]};'
        )
        layout.addWidget(accent)

        # Header with run button
        header = QHBoxLayout()
        title = QLabel('Analysis Results')
        title.setObjectName('pageTitle')
        header.addWidget(title)
        header.addStretch()

        self.run_btn = QPushButton('▶  Run Analysis')
        self.run_btn.setFixedHeight(36)
        self.run_btn.clicked.connect(self._run_analysis)
        header.addWidget(self.run_btn)

        layout.addLayout(header)

        # Progress bar (FR-083)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel('')
        self.progress_label.setObjectName('secondaryText')
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Results tabs
        self.results_tabs = QTabWidget()
        layout.addWidget(self.results_tabs, 1)

        # Tab: Statistics (FR-030)
        self.stats_table = QTableWidget()
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSortingEnabled(True)
        self.results_tabs.addTab(self.stats_table, '📊 Statistics')

        # Tab: Anomalies (FR-035)
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setAlternatingRowColors(True)
        self.anomaly_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.anomaly_table.setSortingEnabled(True)
        self.results_tabs.addTab(self.anomaly_table, '⚠️ Anomalies')

        # Tab: Findings (FR-054)
        self.findings_scroll = QScrollArea()
        self.findings_scroll.setWidgetResizable(True)
        self.findings_widget = QWidget()
        self.findings_layout = QVBoxLayout(self.findings_widget)
        self.findings_scroll.setWidget(self.findings_widget)
        self.results_tabs.addTab(self.findings_scroll, '📋 Findings')

        # Tab: Executive Summary & Recommendations (FR-059, FR-065)
        conclusion_widget = QWidget()
        conclusion_layout = QVBoxLayout(conclusion_widget)

        conclusion_layout.addWidget(QLabel('<b>Executive Summary</b>'))
        self.conclusion_text = QTextEdit()
        self.conclusion_text.setMaximumHeight(120)
        conclusion_layout.addWidget(self.conclusion_text)

        conclusion_layout.addWidget(QLabel('<b>Recommendations</b>'))
        self.recs_text = QTextEdit()
        conclusion_layout.addWidget(self.recs_text)

        # Engineer notes (FR-062)
        note_area = QHBoxLayout()
        note_area.addWidget(QLabel('Engineer Notes:'))
        self.engineer_notes = QTextEdit()
        self.engineer_notes.setMaximumHeight(80)
        self.engineer_notes.setPlaceholderText(
            'Add free-text annotations here before exporting...'
        )
        note_area.addWidget(self.engineer_notes)
        conclusion_layout.addLayout(note_area)

        self.results_tabs.addTab(conclusion_widget, '📝 Executive Summary')

        # Tab: Graphs
        self.graphs_scroll = QScrollArea()
        self.graphs_scroll.setWidgetResizable(True)
        self.graphs_widget = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_widget)
        self.graphs_layout.setAlignment(Qt.AlignTop)
        self.graphs_scroll.setWidget(self.graphs_widget)
        self.results_tabs.addTab(self.graphs_scroll, '📈 Graphs')

        # Tab: Report Export
        self.report_panel = ReportPanel()
        self.results_tabs.addTab(self.report_panel, '📑 Export Report')

        # Placeholder when no data
        self._show_placeholder()

    def set_session_data(self, data: Dict[str, Any]):
        """Set the session data for this panel."""
        self.session_data = data
        self.run_btn.setEnabled(True)
        
        if 'analysis_results' in data:
            self._on_analysis_finished(data['analysis_results'])
        else:
            self._clear_ui()

    def _clear_ui(self):
        """Clear all analysis results from the UI."""
        self.stats_table.setRowCount(0)
        self.anomaly_table.setRowCount(0)
        
        while self.findings_layout.count():
            child = self.findings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.conclusion_text.clear()
        self.recs_text.clear()
        self.engineer_notes.clear()
        
        while self.graphs_layout.count():
            child = self.graphs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_placeholder(self):
        """Show placeholder text when no analysis has been run."""
        self.run_btn.setEnabled(False)

    def _run_analysis(self):
        """Start the analysis pipeline in the background (FR-088)."""
        if not self.session_data:
            return

        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)

        self._worker = AnalysisWorker(self.session_data)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_progress(self, value: int, message: str):
        """Update progress bar and label."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def _on_analysis_finished(self, results: Dict[str, Any]):
        """Populate the UI with analysis results."""
        self.analysis_results = results
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.run_btn.setEnabled(True)

        # Store results in session data for export
        if self.session_data:
            self.session_data['analysis_results'] = results
            # Update DB to mark as Completed
            if self.db_manager:
                sid = self.session_data.get('session_id')
                if sid:
                    insights_dict = results.get('insights', {})
                    all_insights = insights_dict.get('all_insights', [])
                    self.db_manager.update_session(
                        session_id=sid,
                        status='Completed',
                        findings_count=len(all_insights)
                    )

        self._populate_statistics(results['statistics'])
        self._populate_anomalies(results['anomalies'])
        self._populate_findings(results['insights'])
        self._populate_conclusion(results['conclusion'], results['recommendations'])
        self._populate_graphs(results['chart_bytes'])
        
        # Pass to report panel
        self.report_panel.set_results(results)
        
        logger.info('Analysis results displayed.')

    def _on_analysis_error(self, error_msg: str):
        """Handle analysis failure."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, 'Analysis Error', error_msg)
        
        if self.session_data and self.db_manager:
            sid = self.session_data.get('session_id')
            if sid:
                self.db_manager.update_session(
                    session_id=sid,
                    status='Failed',
                    findings_count=0
                )

    def _populate_statistics(self, statistics: Dict[str, Any]):
        """Fill the statistics table (FR-030)."""
        per_column = statistics.get('per_column', {})

        headers = ['Column', 'Mean', 'Median', 'Std Dev', 'Min', 'Max',
                    'Q1', 'Q3', 'IQR', 'Trend']
        self.stats_table.setColumnCount(len(headers))
        self.stats_table.setHorizontalHeaderLabels(headers)
        self.stats_table.setRowCount(len(per_column))

        for row, (col, s) in enumerate(per_column.items()):
            values = [
                col,
                self._fmt(s.get('mean')),
                self._fmt(s.get('median')),
                self._fmt(s.get('std_dev')),
                self._fmt(s.get('min_value')),
                self._fmt(s.get('max_value')),
                self._fmt(s.get('q1')),
                self._fmt(s.get('q3')),
                self._fmt(s.get('iqr')),
                s.get('trend_direction', 'N/A'),
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.stats_table.setItem(row, c, item)

        self.stats_table.resizeColumnsToContents()

    def _populate_anomalies(self, anomalies: Dict[str, Any]):
        """Fill the anomalies table (FR-035, FR-039)."""
        anomaly_list = anomalies.get('anomalies', [])

        headers = ['Column', 'Row', 'Method', 'Severity', 'Value',
                    'Actions']
        self.anomaly_table.setColumnCount(len(headers))
        self.anomaly_table.setHorizontalHeaderLabels(headers)
        self.anomaly_table.setRowCount(len(anomaly_list))

        for row, a in enumerate(anomaly_list):
            col_name = a.get('column_name', '')
            row_ref = a.get('row_reference', '')
            method = a.get('method', '')
            severity = a.get('severity', 'Warning')
            value = a.get('value')

            items = [col_name, str(row_ref), method, severity,
                     self._fmt(value)]
            for c, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                # Color severity column
                if c == 3:
                    sev_color = SEVERITY_COLORS.get(severity, GRAPHITE)
                    item.setForeground(
                        __import__('PyQt5.QtGui', fromlist=['QColor']).QColor(sev_color)
                    )

                self.anomaly_table.setItem(row, c, item)

            # FR-039: False positive button
            fp_btn = QPushButton('Mark FP')
            fp_btn.setFixedHeight(24)
            fp_btn.setStyleSheet(
                f'background-color: {MUTED_SLATE}; font-size: 8pt; padding: 2px 6px;'
            )
            fp_btn.clicked.connect(
                lambda checked, c=col_name, r=row_ref: self._mark_false_positive(c, r)
            )
            self.anomaly_table.setCellWidget(row, 5, fp_btn)

        self.anomaly_table.resizeColumnsToContents()

    def _populate_findings(self, insights: Dict[str, Any]):
        """Fill the findings section (FR-054)."""
        # Clear existing
        while self.findings_layout.count():
            child = self.findings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        grouped = insights.get('grouped_by_column', {})

        if not grouped:
            self.findings_layout.addWidget(QLabel('No findings to report.'))
            return

        for column, findings in grouped.items():
            group = QGroupBox(column)
            group_layout = QVBoxLayout(group)

            for finding in findings:
                severity = finding.get('severity', 'Info')
                text = finding.get('text', '')
                sev_color = SEVERITY_COLORS.get(severity, GRAPHITE)
                bg_color = SEVERITY_BG_COLORS.get(severity, PANEL_WHITE)

                label = QLabel(f'[{severity}] {text}')
                label.setWordWrap(True)
                label.setStyleSheet(
                    f'background-color: {bg_color}; '
                    f'color: {GRAPHITE}; padding: 6px; '
                    f'border-left: 3px solid {sev_color}; '
                    f'border-radius: 2px; margin: 2px 0;'
                )
                group_layout.addWidget(label)

            self.findings_layout.addWidget(group)

        self.findings_layout.addStretch()

    def _populate_conclusion(self, conclusion: str,
                              recommendations: List[Dict[str, Any]]):
        """Fill the conclusion and recommendations (FR-059, FR-065)."""
        self.conclusion_text.setText(conclusion)

        recs_html = []
        for i, rec in enumerate(recommendations, 1):
            severity = rec.get('severity', 'Info')
            text = rec.get('text', '')
            sev_color = SEVERITY_COLORS.get(severity, GRAPHITE)
            recs_html.append(
                f'<p><span style="color:{sev_color};font-weight:bold;">'
                f'[{severity}]</span> {i}. {text}</p>'
            )
        self.recs_text.setHtml(''.join(recs_html) or '<p>No recommendations.</p>')

    def _populate_graphs(self, chart_bytes: Dict[str, bytes]):
        """Render generated charts as QPixmaps in the UI."""
        # Clear existing
        while self.graphs_layout.count():
            child = self.graphs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not chart_bytes:
            self.graphs_layout.addWidget(QLabel('No graphs generated.'))
            return

        from PyQt5.QtGui import QPixmap

        for name, data in chart_bytes.items():
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            # Create a label for the image
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            
            # Create a title label
            title_label = QLabel(f'<b>{name}</b>')
            title_label.setAlignment(Qt.AlignCenter)
            
            # Add to layout with some spacing
            self.graphs_layout.addWidget(title_label)
            self.graphs_layout.addWidget(img_label)
            self.graphs_layout.addSpacing(20)

    def _mark_false_positive(self, column: str, row_ref: int):
        """Mark an anomaly as a false positive (FR-039)."""
        self.excluded_anomalies.add((column, row_ref))
        QMessageBox.information(
            self, 'False Positive',
            f'Marked ({column}, row {row_ref}) as false positive.\n'
            f'Click "Regenerate" to update findings.'
        )
        logger.info('Marked false positive: %s, row %d', column, row_ref)

    @staticmethod
    def _fmt(value, decimals: int = 4) -> str:
        """Format a numeric value for display."""
        if value is None:
            return 'N/A'
        try:
            return f'{float(value):.{decimals}f}'
        except (TypeError, ValueError):
            return str(value)
