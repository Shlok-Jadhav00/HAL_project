"""
AEIA — Import Panel (Module 10)

Provides the dataset import and preview UI. Supports CSV, XLSX, JSON,
TXT, and LOG files via file dialog or drag-and-drop.

FRs implemented: FR-001 through FR-010, FR-081, FR-084.
Layout: implementation_specification.md §7.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/.
"""

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from gui.theme import (
    CONFIRMED_GREEN, MODULE_COLORS,
)

logger = logging.getLogger('aeia.import_panel')


# Standard error messages (implementation_specification.md §9)
ERROR_CANNOT_PARSE = (
    "This file could not be read. It may be corrupted or in an "
    "unsupported format. Please check the file and try again."
)
ERROR_UNSUPPORTED = (
    "This file type isn't supported yet. AEIA currently supports "
    "CSV, XLSX, JSON, TXT, and LOG files."
)


class LoadWorker(QThread):
    """Background thread for loading datasets (FR-088)."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            from core.data_loader import load_dataset
            df, col_types, file_type = load_dataset(self.file_path)
            self.finished.emit({
                'dataframe': df,
                'column_types': col_types,
                'file_type': file_type,
                'file_path': self.file_path,
                'filename': os.path.basename(self.file_path),
                'row_count': len(df),
                'column_count': len(df.columns),
            })
        except FileNotFoundError:
            self.error.emit(ERROR_CANNOT_PARSE)
        except ValueError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            logger.error('Load failed: %s', exc, exc_info=True)
            self.error.emit(ERROR_CANNOT_PARSE)


class ImportPanel(QWidget):
    """Dataset import and preview panel.

    FR-001: Support importing CSV, XLSX, JSON, TXT, and LOG files.
    FR-007: Show a preview of the first N rows.
    FR-010: Store dataset metadata.
    FR-084: Display clear error messages.
    """

    def __init__(self, db_manager=None,
                 on_dataset_loaded: Optional[Callable] = None,
                 parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.on_dataset_loaded = on_dataset_loaded
        self.loaded_data = None
        self._worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the import panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Module accent (color_philosophy.md)
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f'background-color: {MODULE_COLORS["Import"]};')
        layout.addWidget(accent)

        # Title
        title = QLabel('Import Dataset')
        title.setObjectName('pageTitle')
        layout.addWidget(title)

        # Description
        desc = QLabel(
            'Import a CSV, XLSX, JSON, TXT, or LOG file for analysis.'
        )
        desc.setObjectName('secondaryText')
        layout.addWidget(desc)

        # Import button area
        btn_area = QHBoxLayout()
        self.import_btn = QPushButton('📁  Browse & Import...')
        self.import_btn.setFixedHeight(40)
        self.import_btn.setFixedWidth(220)
        self.import_btn.clicked.connect(self._browse_file)
        btn_area.addWidget(self.import_btn)
        btn_area.addStretch()
        layout.addLayout(btn_area)

        # Progress bar (FR-083)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # File info card
        self.info_group = QGroupBox('Dataset Information')
        self.info_group.setVisible(False)
        info_layout = QVBoxLayout(self.info_group)

        self.file_info_label = QLabel('')
        info_layout.addWidget(self.file_info_label)

        layout.addWidget(self.info_group)

        # Preview table (FR-007)
        self.preview_group = QGroupBox('Data Preview (first 20 rows)')
        self.preview_group.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        preview_layout.addWidget(self.preview_table)

        layout.addWidget(self.preview_group, 1)

        # Proceed button (hidden until data is loaded)
        self.proceed_btn = QPushButton('▶  Proceed to Analysis')
        self.proceed_btn.setFixedHeight(40)
        self.proceed_btn.setVisible(False)
        self.proceed_btn.setStyleSheet(
            f'background-color: {CONFIRMED_GREEN};'
        )
        self.proceed_btn.clicked.connect(self._proceed)
        layout.addWidget(self.proceed_btn)

    def _browse_file(self):
        """Open a file dialog to select a dataset (FR-001)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Select Dataset File',
            '',
            'All Supported (*.csv *.xlsx *.xls *.json *.txt *.log);;'
            'CSV Files (*.csv);;'
            'Excel Files (*.xlsx *.xls);;'
            'JSON Files (*.json);;'
            'Text Files (*.txt);;'
            'Log Files (*.log);;'
            'All Files (*)'
        )

        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        """Start loading a dataset file in the background."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.import_btn.setEnabled(False)

        self._worker = LoadWorker(file_path)
        self._worker.finished.connect(self._on_load_finished)
        self._worker.error.connect(self._on_load_error)
        self._worker.start()

    def _on_load_finished(self, data: Dict[str, Any]):
        """Handle successful dataset load."""
        self.loaded_data = data
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)

        # Show file info
        self.file_info_label.setText(
            f'<b>File:</b> {data["filename"]}<br/>'
            f'<b>Type:</b> {data["file_type"]}<br/>'
            f'<b>Rows:</b> {data["row_count"]}<br/>'
            f'<b>Columns:</b> {data["column_count"]}<br/>'
            f'<b>Column Types:</b> {", ".join(f"{k} ({v})" for k, v in data["column_types"].items())}'
        )
        self.info_group.setVisible(True)

        # Populate preview table (FR-007)
        self._populate_preview(data['dataframe'])
        self.preview_group.setVisible(True)
        self.proceed_btn.setVisible(True)

        logger.info('Loaded %s: %d rows, %d cols.',
                     data['filename'], data['row_count'],
                     data['column_count'])

    def _on_load_error(self, error_msg: str):
        """Handle load failure with user-facing error (FR-084)."""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)

        QMessageBox.warning(self, 'Import Error', error_msg)
        logger.warning('Import failed: %s', error_msg)

    def _populate_preview(self, df):
        """Fill the preview table with the first 20 rows (FR-007)."""
        preview = df.head(20)
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels(
            [str(c) for c in preview.columns]
        )

        for row in range(len(preview)):
            for col in range(len(preview.columns)):
                val = preview.iloc[row, col]
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.preview_table.setItem(row, col, item)

        self.preview_table.resizeColumnsToContents()

    def _proceed(self):
        """Pass the loaded dataset to the main window for analysis."""
        if self.loaded_data and self.on_dataset_loaded:
            # Add session metadata
            if self.db_manager:
                dataset_id = self.db_manager.insert_dataset(
                    filename=self.loaded_data['filename'],
                    source_path=self.loaded_data['file_path'],
                    file_type=self.loaded_data['file_type'],
                    row_count=self.loaded_data['row_count'],
                    column_count=self.loaded_data['column_count']
                )
                session_id = self.db_manager.create_session(dataset_id)
                self.loaded_data['session_id'] = session_id
            else:
                self.loaded_data['session_id'] = self.loaded_data.get('session_id', 1)
                
            self.loaded_data['dataset_info'] = {
                'filename': self.loaded_data['filename'],
                'row_count': self.loaded_data['row_count'],
                'column_count': self.loaded_data['column_count'],
                'import_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            self.on_dataset_loaded(self.loaded_data)
