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
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

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
        self.sessions_table = QTableWidget()
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sessions_table.setSortingEnabled(True)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sessions_table.setColumnCount(6)
        self.sessions_table.setHorizontalHeaderLabels([
            'Session ID', 'Dataset', 'Started', 'Status',
            'Findings', 'Actions',
        ])
        self.sessions_table.horizontalHeader().setStretchLastSection(True)

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
        self.sessions_table.setRowCount(len(sessions))

        for row, session in enumerate(sessions):
            # Fetch dataset name
            dataset_name = 'Unknown'
            dataset = self.db_manager.get_dataset(session.dataset_id)
            if dataset:
                dataset_name = dataset.filename

            items = [
                str(session.session_id),
                dataset_name,
                str(session.started_on),
                session.status,
                str(session.findings_count),
            ]

            for col, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                # Color status column
                if col == 3:
                    status = val
                    if status == 'Completed':
                        item.setForeground(
                            __import__('PyQt5.QtGui', fromlist=['QColor']).QColor(CONFIRMED_GREEN)
                        )
                    elif status == 'Failed':
                        item.setForeground(
                            __import__('PyQt5.QtGui', fromlist=['QColor']).QColor(SEVERITY_COLORS.get('Critical', ''))
                        )

                self.sessions_table.setItem(row, col, item)

            # Re-open button (FR-100)
            open_btn = QPushButton('Open')
            open_btn.setFixedHeight(24)
            open_btn.setStyleSheet('font-size: 8pt; padding: 2px 8px;')
            sid = session.session_id
            open_btn.clicked.connect(
                lambda checked, s=sid: self._open_session(s)
            )
            self.sessions_table.setCellWidget(row, 5, open_btn)

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
        for item in selected:
            rows.add(item.row())

        session_ids = []
        for row in rows:
            sid_item = self.sessions_table.item(row, 0)
            if sid_item:
                session_ids.append(sid_item.text())

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
