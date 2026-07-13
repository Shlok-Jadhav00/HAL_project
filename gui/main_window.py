"""
AEIA — Main Window (Module 10)

The primary PyQt5 application window with a persistent sidebar,
tab-based dataset sessions, and status bar.

FRs implemented: FR-081 through FR-090.
Layout: implementation_specification.md §7.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/ (code_hygiene_guide.md).
"""

import logging
from typing import Any, Dict

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QShortcut, QStackedWidget, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget,
)

from gui.theme import (
    BODY_FONT_SIZE, MUTED_SLATE, PAGE_TITLE_FONT_SIZE, SIDEBAR_WIDTH,
    WINDOW_HEIGHT, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_WIDTH,
)
from gui.import_panel import ImportPanel
from gui.analysis_panel import AnalysisPanel
from gui.history_panel import HistoryPanel
from gui.settings_dialog import SettingsDialog

from core import __version__

logger = logging.getLogger('aeia.main_window')


# ---------------------------------------------------------------------------
# Worker thread for background analysis (FR-088)
# ---------------------------------------------------------------------------

class AnalysisWorker(QThread):
    """Background thread for running analysis without freezing UI.

    FR-088: GUI shall remain responsive during long-running analysis.
    """
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, session_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.session_data = session_data

    def run(self):
        """Execute the full analysis pipeline in a background thread."""
        try:
            from core.preprocessor import preprocess_dataset
            from core.statistics_engine import compute_statistics
            from core.anomaly_detector import detect_anomalies
            from core.expert_system import load_rules, evaluate_rules
            from core.insight_generator import generate_insights
            from core.recommendation_engine import (
                generate_conclusion, generate_recommendations,
            )

            df = self.session_data['dataframe']
            col_types = self.session_data['column_types']

            # Step 1: Preprocess
            self.progress.emit(10, 'Preprocessing...')
            df_clean, preprocess_log = preprocess_dataset(df, col_types)

            # Step 2: Statistics
            self.progress.emit(30, 'Computing statistics...')
            measurement_types = {
                k: v for k, v in col_types.items()
                if k != 'Sample_ID'
            }
            stats = compute_statistics(df_clean, measurement_types)

            # Step 3: Anomaly detection
            self.progress.emit(50, 'Detecting anomalies...')
            anomalies = detect_anomalies(df_clean, measurement_types)

            # Step 4: Expert system
            self.progress.emit(65, 'Evaluating rules...')
            from core.config_manager import get_rules_path
            rules_path = self.session_data.get('rules_path') or get_rules_path()
            rules = load_rules(rules_path)
            matches = evaluate_rules(rules, stats, anomalies, df=df_clean)

            # Step 5: Insight generation
            self.progress.emit(80, 'Generating insights...')
            dataset_info = self.session_data.get('dataset_info', {})
            insights = generate_insights(
                stats, anomalies, matches, dataset_info
            )

            # Step 6: Conclusions & recommendations
            self.progress.emit(90, 'Building conclusion...')
            conclusion = generate_conclusion(insights)
            recs = generate_recommendations(insights, matches)

            self.progress.emit(100, 'Analysis complete.')

            result = {
                'dataframe': df_clean,
                'column_types': col_types,
                'preprocess_log': preprocess_log,
                'statistics': stats,
                'anomalies': anomalies,
                'rules': rules,
                'rule_matches': matches,
                'insights': insights,
                'conclusion': conclusion,
                'recommendations': recs,
                'dataset_info': dataset_info,
            }
            self.finished.emit(result)

        except Exception as exc:
            logger.error('Analysis failed: %s', exc, exc_info=True)
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """AEIA main application window.

    FR-081: Import → Preprocess → Analyze → Review → Export workflow.
    FR-082: Persistent sidebar for Import, Analysis, History, Settings.
    FR-085: Tabbed dataset sessions.
    FR-086: Status bar with dataset name, row count, timestamp.
    FR-087: Keyboard shortcuts (Ctrl+O, Ctrl+E).
    FR-089: About/Help panel.
    """

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.sessions = {}  # session_id → session_data
        self.current_session_id = None

        self._setup_window()
        self._setup_sidebar()
        self._setup_content_area()
        self._setup_status_bar()
        self._setup_menu_bar()

        logger.info('Main window initialized.')

    def _setup_window(self):
        """Configure the main window properties (§7)."""
        self.setWindowTitle(f'AEIA — AI-Powered Engineering Insight Assistant v{__version__}')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    def _setup_sidebar(self):
        """Build the persistent sidebar (FR-082).

        Items in fixed order: Import, Analysis, History, Settings.
        """
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(2)

        # App branding
        brand = QLabel('AEIA')
        brand.setStyleSheet(
            f'color: white; font-size: {PAGE_TITLE_FONT_SIZE}pt; '
            f'font-weight: bold; padding: 10px 16px;'
        )
        layout.addWidget(brand)
        layout.addSpacing(20)

        # Sidebar items (FR-082: fixed order)
        self.sidebar_buttons = {}
        items = [
            ('Import', '📥', 0),
            ('Analysis', '📊', 1),
            ('History', '📋', 2),
            ('Settings', '⚙️', 3),
        ]

        for name, icon, index in items:
            btn = QPushButton(f'  {icon}  {name}')
            btn.setObjectName(f'sidebar_{name.lower()}')
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setStyleSheet(
                f'QPushButton {{ text-align: left; font-size: {BODY_FONT_SIZE}pt; }}'
            )
            btn.clicked.connect(lambda checked, idx=index: self._switch_panel(idx))
            layout.addWidget(btn)
            self.sidebar_buttons[name] = btn

        layout.addStretch()

        # Version label
        ver_label = QLabel(f'v{__version__}')
        ver_label.setStyleSheet(
            f'color: {MUTED_SLATE}; font-size: 8pt; padding: 10px 16px;'
        )
        layout.addWidget(ver_label)

        self.sidebar = sidebar

    def _setup_content_area(self):
        """Build the main content area with stacked panels and session tabs."""
        # Central widget
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add sidebar
        main_layout.addWidget(self.sidebar)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 8)
        content_layout.setSpacing(8)

        # Session tabs (FR-085)
        self.session_tabs = QTabWidget()
        self.session_tabs.setTabsClosable(True)
        self.session_tabs.tabCloseRequested.connect(self._close_session_tab)
        self.session_tabs.currentChanged.connect(self._on_tab_changed)

        # Stacked widget for sidebar panels
        self.panel_stack = QStackedWidget()

        # Create panels
        self.import_panel = ImportPanel(
            db_manager=self.db_manager,
            on_dataset_loaded=self._on_dataset_loaded,
        )
        self.analysis_panel = AnalysisPanel(
            db_manager=self.db_manager,
        )
        self.history_panel = HistoryPanel(
            db_manager=self.db_manager,
        )
        self.settings_panel = SettingsDialog()

        self.panel_stack.addWidget(self.import_panel)
        self.panel_stack.addWidget(self.analysis_panel)
        self.panel_stack.addWidget(self.history_panel)
        self.panel_stack.addWidget(self.settings_panel)

        # Tab area at top, panel stack below
        content_layout.addWidget(self.session_tabs)
        content_layout.addWidget(self.panel_stack, 1)

        main_layout.addWidget(content, 1)

        self.setCentralWidget(central)

        # Start on Import panel
        self._switch_panel(0)

    def _setup_status_bar(self):
        """Build the status bar (FR-086)."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_dataset_label = QLabel('No dataset loaded')
        self.status_row_label = QLabel('')
        self.status_timestamp_label = QLabel('')

        self.status_bar.addWidget(self.status_dataset_label, 1)
        self.status_bar.addWidget(self.status_row_label)
        self.status_bar.addPermanentWidget(self.status_timestamp_label)

    def _setup_menu_bar(self):
        """Build the menu bar with File and Help menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('&File')

        import_action = QAction('&Import Dataset...', self)
        import_action.setShortcut('Ctrl+O')
        import_action.triggered.connect(lambda: self._switch_panel(0))
        file_menu.addAction(import_action)

        export_action = QAction('&Export Report...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self._export_report)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts directly (FR-087)."""
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_O:
                self._switch_panel(0)
                event.accept()
                return
            elif event.key() == Qt.Key_E:
                self._export_report()
                event.accept()
                return
        super().keyPressEvent(event)

        # Help menu (FR-089)
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About AEIA', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # -------------------------------------------------------------------
    # Panel switching
    # -------------------------------------------------------------------

    def _switch_panel(self, index: int):
        """Switch the active panel in the stacked widget."""
        self.panel_stack.setCurrentIndex(index)

        # Update sidebar button states
        names = ['Import', 'Analysis', 'History', 'Settings']
        for i, name in enumerate(names):
            btn = self.sidebar_buttons.get(name)
            if btn:
                btn.setChecked(i == index)

    # -------------------------------------------------------------------
    # Dataset loading (from ImportPanel)
    # -------------------------------------------------------------------

    def _on_dataset_loaded(self, data: Dict[str, Any]):
        """Handle a newly loaded dataset from the import panel.

        Creates a new session tab and switches to Analysis view.
        """
        filename = data.get('filename', 'unknown')
        session_id = data.get('session_id', len(self.sessions) + 1)

        self.sessions[session_id] = data
        self.current_session_id = session_id

        # Add tab (FR-085)
        tab_index = self.session_tabs.addTab(
            QWidget(), f'{filename} (S{session_id:05d})'
        )
        self.session_tabs.setCurrentIndex(tab_index)

        # Update status bar (FR-086)
        row_count = data.get('row_count', 0)
        self.status_dataset_label.setText(f'Dataset: {filename}')
        self.status_row_label.setText(f'Rows: {row_count}')

        # Switch to Analysis panel
        self._switch_panel(1)
        self.analysis_panel.set_session_data(data)

        logger.info('Session %d loaded: %s (%d rows)',
                     session_id, filename, row_count)

    # -------------------------------------------------------------------
    # Session tab management
    # -------------------------------------------------------------------

    def _close_session_tab(self, index: int):
        """Close a session tab."""
        self.session_tabs.removeTab(index)
        if self.session_tabs.count() == 0:
            self.status_dataset_label.setText('No dataset loaded')
            self.status_row_label.setText('')

    def _on_tab_changed(self, index: int):
        """Handle tab switching — update the active session context."""
        if index >= 0 and self.session_tabs.count() > 0:
            # Find the session data for this tab
            tab_text = self.session_tabs.tabText(index)
            for sid, data in self.sessions.items():
                if f'S{sid:05d}' in tab_text:
                    self.current_session_id = sid
                    self.analysis_panel.set_session_data(data)
                    break

    # -------------------------------------------------------------------
    # Report export
    # -------------------------------------------------------------------

    def _export_report(self):
        """Export a report for the current session (FR-075)."""
        if self.current_session_id is None:
            QMessageBox.information(
                self, 'No Session',
                'Please import and analyze a dataset before exporting.'
            )
            return

        session_data = self.sessions.get(self.current_session_id, {})
        results = session_data.get('analysis_results')

        if not results:
            QMessageBox.information(
                self, 'No Analysis',
                'Please run analysis before exporting a report.'
            )
            return

        from core.config_manager import get_reports_path
        import os
        
        # Ask for save location (FR-075)
        reports_dir = get_reports_path()
        os.makedirs(reports_dir, exist_ok=True)
        
        default_name = f'AEIA_Report_S{self.current_session_id:05d}.pdf'
        default_path = os.path.join(reports_dir, default_name)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Report', default_path,
            'PDF Files (*.pdf);;CSV Files (*.csv);;All Files (*)'
        )

        if not file_path:
            return

        try:
            from core.report_builder import (
                generate_pdf_report, generate_csv_export,
            )
            from core.chart_builder import (
                generate_all_charts,
            )

            if file_path.lower().endswith('.csv'):
                generate_csv_export(
                    file_path,
                    results['statistics'],
                    results['anomalies'],
                )
            else:
                # Generate charts
                chart_bytes = generate_all_charts(
                    results['dataframe'],
                    results['statistics'],
                    results['anomalies'],
                    results['column_types'],
                )

                generate_pdf_report(
                    file_path,
                    results['dataset_info'],
                    self.current_session_id,
                    results['statistics'],
                    results['anomalies'],
                    results['insights'],
                    results['conclusion'],
                    results['recommendations'],
                    charts=chart_bytes,
                )

            QMessageBox.information(
                self, 'Export Complete',
                f'Report saved to:\n{file_path}'
            )
            self.status_bar.showMessage(f'Report exported: {file_path}', 5000)

        except Exception as exc:
            logger.error('Report export failed: %s', exc, exc_info=True)
            QMessageBox.critical(
                self, 'Export Failed',
                'The report could not be saved to the selected location. '
                'Please check that the folder exists and that you have '
                'permission to write to it.'
            )

    # -------------------------------------------------------------------
    # About dialog (FR-089)
    # -------------------------------------------------------------------

    def _show_about(self):
        """Show the About dialog (FR-089)."""
        QMessageBox.about(
            self,
            'About AEIA',
            f'<h2>AEIA</h2>'
            f'<p><b>AI-Powered Engineering Insight Assistant</b></p>'
            f'<p>Version {__version__}</p>'
            f'<br/>'
            f'<p>An offline desktop application for avionics and aerospace '
            f'engineers. Imports datasets, runs statistical analysis, '
            f'anomaly detection, and a rule-based expert system, then '
            f'exports a PDF report with plain-language findings and '
            f'recommendations.</p>'
            f'<br/>'
            f'<p><b>Key Features:</b></p>'
            f'<ul>'
            f'<li>100% offline, CPU-only operation</li>'
            f'<li>Z-score, IQR, and Isolation Forest anomaly detection</li>'
            f'<li>Rule-based expert system with editable rules</li>'
            f'<li>Template-based, explainable NLG</li>'
            f'<li>PDF/CSV report export</li>'
            f'</ul>'
        )
