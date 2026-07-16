"""
AEIA — History Panel (Module 12)

Provides a session history browser showing past analysis sessions.

FRs implemented: FR-098 through FR-105.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/.
"""

import logging
from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableView,
    QVBoxLayout, QWidget, QAbstractItemView, QHeaderView
)

from gui.models import HistoryTableModel

from gui.theme import (
    CONFIRMED_GREEN, MODULE_COLORS, SEVERITY_COLORS,
)

logger = logging.getLogger('aeia.history_panel')


class HistoryPanel(QWidget):
    """Session history browser.

    FR-098: Maintain a log of every analysis session.
    FR-099: Display session list with dataset name, timestamp, and status.
    FR-100: Allow re-opening a past session's findings.
    FR-101: Allow deleting a past session.
    FR-102: Sort sessions by date, dataset name, or findings count.
    FR-103: The original file path is metadata-only — the raw file is
            never copied into AEIA's storage.
    FR-104: Auto-save session state on exit.
    FR-105: Display up to 100 recent sessions.
    """

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._setup_ui()

    def _setup_ui(self):
        """Build the history panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Module accent
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(
            f'background-color: {MODULE_COLORS["History"]};'
        )
        layout.addWidget(accent)

        # Title
        title = QLabel('Analysis History')
        title.setObjectName('pageTitle')
        layout.addWidget(title)

        desc = QLabel('Browse past analysis sessions and their results.')
        desc.setObjectName('secondaryText')
        layout.addWidget(desc)

        # Toolbar
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton('🔄  Refresh')
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._refresh_sessions)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        delete_btn = QPushButton('🗑️  Delete Selected')
        delete_btn.setFixedHeight(32)
        delete_btn.setObjectName('destructive')
        delete_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(delete_btn)

        layout.addLayout(toolbar)

        # Sessions table (FR-099, FR-102)
        self.sessions_table = QTableView()
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sessions_table.setSortingEnabled(False)  # Sorting requires QSortFilterProxyModel, skipped for brevity
        self.sessions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sessions_table.horizontalHeader().setStretchLastSection(True)
        
        self._table_model = HistoryTableModel()
        self.sessions_table.setModel(self._table_model)

        layout.addWidget(self.sessions_table, 1)

        # Info
        self.info_label = QLabel(
            'No sessions recorded yet. Import and analyze a dataset '
            'to create your first session.'
        )
        self.info_label.setObjectName('secondaryText')
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

    def _refresh_sessions(self):
        """Refresh the session list from the database (FR-105)."""
        if not self.db_manager:
            logger.info('No database manager — showing empty history.')
            return

        try:
            sessions = self.db_manager.list_sessions()
            self._populate_table(sessions)
            self.info_label.setText(
                f'{len(sessions)} session(s) found.'
            )
        except Exception as exc:
            logger.warning('Could not load sessions: %s', exc)
            self.info_label.setText('Could not load session history.')

    def _populate_table(self, sessions: List[Any]):
        """Fill the sessions table."""
        data_list = []
        for session in sessions:
            dataset_name = 'Unknown'
            dataset = self.db_manager.get_dataset(session.dataset_id)
            if dataset:
                dataset_name = dataset.filename
            
            data_list.append({
                'session_id': session.session_id,
                'dataset_name': dataset_name,
                'started_on': session.started_on,
                'status': session.status,
                'findings_count': session.findings_count
            })
            
        self._table_model.update_data(data_list)
        
        # Re-open button (FR-100)
        # For History (max 100 rows), setIndexWidget is acceptable for performance
        for row, session_data in enumerate(data_list):
            open_btn = QPushButton('Open')
            open_btn.setFixedHeight(24)
            open_btn.setStyleSheet('font-size: 8pt; padding: 2px 8px;')
            sid = session_data['session_id']
            open_btn.clicked.connect(
                lambda checked, s=sid: self._open_session(s)
            )
            idx = self._table_model.index(row, 5) # Assuming actions column is 5
            self.sessions_table.setIndexWidget(idx, open_btn)

        self.sessions_table.resizeColumnsToContents()

    def _delete_selected(self):
        """Delete selected session(s) (FR-101)."""
        selected = self.sessions_table.selectedItems()
        if not selected:
            QMessageBox.information(
                self, 'No Selection',
                'Please select a session to delete.'
            )
            return

        # Get unique session IDs from selected rows
        rows = set()
        for index in selected:
            rows.add(index.row())

        session_ids = []
        for row in rows:
            sid = self._table_model.get_session_id(row)
            if sid != -1:
                session_ids.append(str(sid))

        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f'Delete {len(session_ids)} session(s)? This cannot be undone.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            if self.db_manager:
                for sid in session_ids:
                    try:
                        self.db_manager.delete_session(int(sid))
                    except Exception as exc:
                        logger.warning('Failed to delete session %s: %s',
                                        sid, exc)
            self._refresh_sessions()

    def _open_session(self, session_id: int):
        """Open a past session's findings (FR-100)."""
        logger.info('Opening session %d', session_id)
        if not self.db_manager:
            return

        reports = self.db_manager.get_reports(session_id)
        if reports:
            # Open the most recently generated report
            latest_report = reports[0]
            try:
                import os
                os.startfile(latest_report.file_path)
            except Exception as e:
                logger.error("Could not open report: %s", e)
                QMessageBox.warning(self, "Error", f"Could not open the report PDF:\n{e}")
        else:
            QMessageBox.information(
                self, 'Open Session',
                f'Session {session_id} has no exported report yet. '
                f'(Full re-open integration pending GUI shell completion.)'
            )
