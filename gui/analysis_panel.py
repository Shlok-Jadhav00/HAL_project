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
    QAbstractItemView, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QTableView, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget, QStackedWidget
)

from gui.models import AnomalyTableModel
from gui.theme import (
    GRAPHITE, MODULE_COLORS, MUTED_SLATE, PANEL_WHITE,
    SEVERITY_BG_COLORS, SEVERITY_COLORS, SEVERITY_TEXT_COLORS,
    STEEL_LINE, CONFIRMED_GREEN, SIGNAL_BLUE
)
from gui.report_panel import ReportPanel

logger = logging.getLogger('aeia.analysis_panel')


class AnalysisWorker(QThread):
    """Background thread for running the full analysis pipeline (FR-088)."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, session_data: Dict[str, Any], excluded_anomalies: set = None, parent=None):
        super().__init__(parent)
        self.session_data = session_data
        self.excluded_anomalies = excluded_anomalies or set()

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
                if_n_estimators=det_cfg.get('isolation_forest_n_estimators', 50),
                if_random_state=det_cfg.get('isolation_forest_random_state', 42),
                if_n_jobs=det_cfg.get('isolation_forest_n_jobs', 1)
            )

            # Remove false positives (FR-039)
            if self.excluded_anomalies and 'anomalies' in anomalies:
                anomalies['anomalies'] = [
                    a for a in anomalies['anomalies']
                    if (a.get('column_name'), a.get('row_reference')) not in self.excluded_anomalies
                ]

            self.progress.emit(65, 'Evaluating rules...')
            rules_path = get_rules_path()
            rules = load_rules(rules_path)
            matches = evaluate_rules(rules, stats, anomalies, df=df_clean)

            self.progress.emit(80, 'Generating insights...')
            dataset_info = self.session_data.get('dataset_info', {})
            insights = generate_insights(
                stats, anomalies, matches, dataset_info, self.excluded_anomalies
            )

            self.progress.emit(90, 'Building conclusion...')
            conclusion = generate_conclusion(insights)
            recs = generate_recommendations(insights, matches)

            self.progress.emit(100, 'Analysis complete.')

            # Return all computed data
            results = {
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
                'charts': {}, # Phase 5: Lazy load charts when exporting PDF
            }
            self.finished.emit(results)

        except Exception as exc:
            logger.error('Analysis failed: %s', exc, exc_info=True)
            self.error.emit(str(exc))


class ChartWorker(QThread):
    """Background thread for generating charts on-demand in the UI."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, analysis_results: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.analysis_results = analysis_results

    def run(self):
        try:
            from core.chart_builder import generate_all_charts
            
            df = self.analysis_results['dataframe']
            measurement_types = self.analysis_results['measurement_types']
            stats = self.analysis_results['statistics']
            anomalies = self.analysis_results['anomalies']

            self.progress.emit(0, 'Generating charts...')
            chart_bytes = generate_all_charts(df, stats, anomalies, measurement_types)
            
            self.progress.emit(100, 'Charts complete.')
            self.finished.emit(chart_bytes)
        except Exception as exc:
            logger.error('Chart generation failed: %s', exc, exc_info=True)
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

        # Dashboard Cards (FR-051, FR-086, FR-038, FR-061, FR-083, FR-071)
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QHBoxLayout(self.dashboard_widget)
        self.dashboard_layout.setContentsMargins(0, 0, 0, 0)
        self.dashboard_layout.setSpacing(8)
        self.dashboard_widget.setVisible(False)
        layout.addWidget(self.dashboard_widget)

        # Results tabs
        self.results_tabs = QTabWidget()
        layout.addWidget(self.results_tabs, 1)

        # Tab: Statistics (FR-030)
        self.stats_table = QTableWidget()
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSortingEnabled(True)
        self.stats_table.setMouseTracking(True)
        self.stats_table.setStyleSheet("QTableWidget::item:hover { background-color: #EFF6FF; color: #111827; }")
        self.results_tabs.addTab(self.stats_table, '📊 Statistics')

        # Tab: Anomalies (FR-035)
        self.anomaly_table = QTableView()
        self.anomaly_table.setAlternatingRowColors(True)
        self.anomaly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.anomaly_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.anomaly_table.setSortingEnabled(False)
        self.anomaly_table.horizontalHeader().setStretchLastSection(True)
        self.anomaly_table.setMouseTracking(True)
        self.anomaly_table.setStyleSheet("QTableView::item:hover { background-color: #EFF6FF; color: #111827; }")
        
        self._anomaly_model = AnomalyTableModel()
        self.anomaly_table.setModel(self._anomaly_model)
        self.anomaly_table.clicked.connect(self._on_anomaly_clicked)
        
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
        self.graphs_stack = QStackedWidget()

        # Graphs: Placeholder State
        self.graphs_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.graphs_placeholder)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        
        self.graphs_msg_label = QLabel('Charts are generated on demand to keep analysis fast.')
        self.graphs_msg_label.setStyleSheet(f"color: {MUTED_SLATE}; font-size: 11pt;")
        
        self.generate_charts_btn = QPushButton('📊 Generate Charts')
        self.generate_charts_btn.setFixedWidth(200)
        self.generate_charts_btn.setFixedHeight(40)
        self.generate_charts_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {SIGNAL_BLUE}; font-weight: bold; font-size: 11pt; color: white; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
            QPushButton:disabled {{ background-color: {STEEL_LINE}; color: {MUTED_SLATE}; }}
        """)
        self.generate_charts_btn.clicked.connect(self._on_generate_charts_clicked)
        
        placeholder_layout.addWidget(self.graphs_msg_label, alignment=Qt.AlignCenter)
        placeholder_layout.addSpacing(15)
        placeholder_layout.addWidget(self.generate_charts_btn, alignment=Qt.AlignCenter)

        # Graphs: Rendered State
        self.graphs_scroll = QScrollArea()
        self.graphs_scroll.setWidgetResizable(True)
        self.graphs_widget = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_widget)
        self.graphs_layout.setAlignment(Qt.AlignTop)
        self.graphs_scroll.setWidget(self.graphs_widget)

        self.graphs_stack.addWidget(self.graphs_placeholder)
        self.graphs_stack.addWidget(self.graphs_scroll)
        self.graphs_stack.setCurrentWidget(self.graphs_placeholder)

        self.results_tabs.addTab(self.graphs_stack, '📈 Graphs')

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
        self._anomaly_model.update_data([])
        
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
        self.graphs_msg_label.setText('Charts are generated on demand to keep analysis fast.')
        self.generate_charts_btn.show()
        self.generate_charts_btn.setEnabled(True)
        self.graphs_stack.setCurrentWidget(self.graphs_placeholder)
                
        self.dashboard_widget.setVisible(False)
        while self.dashboard_layout.count():
            child = self.dashboard_layout.takeAt(0)
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

        self._worker = AnalysisWorker(self.session_data, self.excluded_anomalies)
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
        
        # If charts were cached in session, show them; else reset to placeholder
        charts = results.get('charts', {})
        if charts:
            self._populate_graphs(charts)
        else:
            self.graphs_msg_label.setText('Charts are generated on demand to keep analysis fast.')
            self.generate_charts_btn.show()
            self.generate_charts_btn.setEnabled(True)
            self.graphs_stack.setCurrentWidget(self.graphs_placeholder)

        self._populate_dashboard(results)
        
        # Pass to report panel
        self.report_panel.set_results(results)
        
        logger.info('Analysis results displayed.')

    def _on_generate_charts_clicked(self):
        """Handle on-demand chart generation request."""
        if not hasattr(self, 'analysis_results') or not self.analysis_results:
            return

        df = self.analysis_results.get('dataframe')
        if df is None:
            return

        if len(df) > 10000:
            reply = QMessageBox.question(
                self, 'Generate Charts',
                f'This dataset has {len(df):,} rows. Generating interactive charts '
                'may take several seconds. Do you want to proceed?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return

        self.generate_charts_btn.setEnabled(False)
        self.generate_charts_btn.hide()
        self.graphs_msg_label.setText('Generating charts... Please wait.')

        self._chart_worker = ChartWorker(self.analysis_results)
        self._chart_worker.finished.connect(self._on_charts_finished)
        self._chart_worker.error.connect(self._on_charts_error)
        self._chart_worker.start()

    def _on_charts_finished(self, chart_bytes: Dict[str, bytes]):
        """Handle completion of chart generation."""
        self.analysis_results['charts'] = chart_bytes
        if self.session_data:
            self.session_data['analysis_results']['charts'] = chart_bytes
        self._populate_graphs(chart_bytes)

    def _on_charts_error(self, error_msg: str):
        """Handle chart generation failure."""
        QMessageBox.warning(self, 'Chart Error', f'Failed to generate charts: {error_msg}')
        self.graphs_msg_label.setText('Failed to generate charts.')
        self.generate_charts_btn.show()
        self.generate_charts_btn.setEnabled(True)

    def _populate_dashboard(self, results: Dict[str, Any]):
        """Populate the 6 Session Dashboard Cards."""
        while self.dashboard_layout.count():
            child = self.dashboard_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        dataset_info = results.get('dataset_info', {})
        insights_dict = results.get('insights', {})
        all_insights = insights_dict.get('all_insights', [])
        
        crit_count = sum(1 for i in all_insights if i.get('severity') == 'Critical')
        warn_count = sum(1 for i in all_insights if i.get('severity') == 'Warning')
        info_count = sum(1 for i in all_insights if i.get('severity') == 'Info')

        def make_card(title: str, value: str, color: str = GRAPHITE) -> QWidget:
            card = QWidget()
            card.setStyleSheet(f"background-color: {PANEL_WHITE}; border: 1px solid {STEEL_LINE}; border-radius: 4px;")
            l = QVBoxLayout(card)
            l.setContentsMargins(12, 12, 12, 12)
            l.setSpacing(4)
            
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color: {MUTED_SLATE}; border: none; font-size: 9pt;")
            
            v_lbl = QLabel(value)
            v_lbl.setStyleSheet(f"color: {color}; border: none; font-size: 14pt; font-weight: bold;")
            
            l.addWidget(t_lbl)
            l.addWidget(v_lbl)
            return card

        crit_color = SEVERITY_COLORS['Critical'] if crit_count > 0 else CONFIRMED_GREEN
        
        self.dashboard_layout.addWidget(make_card("Dataset", f"{dataset_info.get('filename', 'Unknown')}"))
        self.dashboard_layout.addWidget(make_card("Critical Findings", str(crit_count), crit_color))
        self.dashboard_layout.addWidget(make_card("Warning Findings", str(warn_count), SEVERITY_COLORS['Warning'] if warn_count > 0 else GRAPHITE))
        self.dashboard_layout.addWidget(make_card("Info Findings", str(info_count), SEVERITY_COLORS['Info'] if info_count > 0 else GRAPHITE))
        self.dashboard_layout.addWidget(make_card("Duration", "0.2s")) # FR-083 (placeholder for timing)
        self.dashboard_layout.addWidget(make_card("Report", "Not Exported"))

        self.dashboard_widget.setVisible(True)

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
        self._anomaly_model.update_data(anomaly_list)
        self.anomaly_table.resizeColumnsToContents()

    def _on_anomaly_clicked(self, index):
        """Handle clicks on the anomaly table (FR-039 False Positive)."""
        if index.isValid() and index.column() == 5: # Actions column
            col, row_ref = self._anomaly_model.get_anomaly_info(index.row())
            if col and row_ref != -1:
                self._mark_false_positive(col, row_ref)

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
                text_color = SEVERITY_TEXT_COLORS.get(severity, GRAPHITE)

                label = QLabel(f'[{severity}] {text}')
                label.setWordWrap(True)
                label.setStyleSheet(
                    f'background-color: {bg_color}; '
                    f'color: {text_color}; padding: 6px; '
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
            
        self.graphs_stack.setCurrentWidget(self.graphs_scroll)

    def _mark_false_positive(self, column: str, row_ref: int):
        """Mark an anomaly as a false positive (FR-039)."""
        self.excluded_anomalies.add((column, row_ref))
        QMessageBox.information(
            self, 'False Positive',
            f'Marked ({column}, row {row_ref}) as false positive.\n'
            f'Click "Run Analysis" to update findings.'
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
