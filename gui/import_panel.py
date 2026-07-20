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
    QVBoxLayout, QWidget, QStackedWidget
)

from gui.theme import (
    CONFIRMED_GREEN, MODULE_COLORS, PREVIEW_ROW_COUNT, 
    SIGNAL_BLUE, STEEL_LINE, PANEL_WHITE, MUTED_SLATE, GRAPHITE
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

        # Progress bar (FR-083)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self._build_initial_state()
        self._build_preview_state()

        self.stack.addWidget(self.initial_widget)
        self.stack.addWidget(self.preview_widget)
        self.stack.setCurrentWidget(self.initial_widget)

    def _build_initial_state(self):
        self.initial_widget = QWidget()
        init_layout = QHBoxLayout(self.initial_widget)
        init_layout.setContentsMargins(0, 0, 0, 0)
        init_layout.setSpacing(16)

        # New Import Card (Left)
        new_import_card = QGroupBox('New Import')
        new_import_card.setStyleSheet(f"QGroupBox {{ padding: 24px; margin-top: 10px; background-color: {PANEL_WHITE}; border: 1px dashed {STEEL_LINE}; border-radius: 6px; }}")
        new_layout = QVBoxLayout(new_import_card)
        new_layout.setAlignment(Qt.AlignCenter)

        new_layout.addStretch()
        
        self.import_btn = QPushButton('📁  Browse Files')
        self.import_btn.setFixedHeight(48)
        self.import_btn.setFixedWidth(240)
        self.import_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {SIGNAL_BLUE}; font-weight: bold; font-size: 12pt; }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
        """)
        self.import_btn.clicked.connect(self._browse_file)
        new_layout.addWidget(self.import_btn, alignment=Qt.AlignCenter)

        formats_label = QLabel('Supported formats: CSV, XLSX, JSON, TXT, LOG')
        formats_label.setStyleSheet(f"color: {MUTED_SLATE}; margin-top: 16px;")
        new_layout.addWidget(formats_label, alignment=Qt.AlignCenter)

        new_layout.addStretch()
        init_layout.addWidget(new_import_card, 2)

        # Recent Datasets Card (Right)
        recent_card = QGroupBox('Recent Datasets')
        recent_card.setStyleSheet(f"QGroupBox {{ padding: 16px; margin-top: 10px; background-color: {PANEL_WHITE}; border: 1px solid {STEEL_LINE}; border-radius: 6px; }}")
        self.recent_layout = QVBoxLayout(recent_card)
        self.recent_layout.setAlignment(Qt.AlignTop)
        
        init_layout.addWidget(recent_card, 1)
        self._populate_recent_datasets()

    def _populate_recent_datasets(self):
        # Clear existing
        while self.recent_layout.count():
            child = self.recent_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not self.db_manager:
            self.recent_layout.addWidget(QLabel("Database not available."))
            return

        try:
            datasets = self.db_manager.list_datasets()
            if not datasets:
                empty = QLabel("No recent datasets.")
                empty.setStyleSheet(f"color: {MUTED_SLATE};")
                self.recent_layout.addWidget(empty)
                return

            for ds in datasets[:5]: # Top 5
                btn = QPushButton(f"📄 {ds.filename}")
                btn.setStyleSheet(f"""
                    QPushButton {{ text-align: left; background-color: transparent; border: 1px solid {STEEL_LINE}; color: {GRAPHITE}; padding: 10px; }}
                    QPushButton:hover {{ background-color: #EFF6FF; border-color: {SIGNAL_BLUE}; }}
                """)
                # Store source_path in closure
                btn.clicked.connect(lambda checked, path=ds.source_path: self._load_recent_file(path))
                self.recent_layout.addWidget(btn)
                
                info = QLabel(f"{ds.row_count} rows • {ds.imported_on.split()[0]}")
                info.setStyleSheet(f"color: {MUTED_SLATE}; font-size: 8pt; margin-left: 28px; margin-bottom: 8px;")
                self.recent_layout.addWidget(info)
                
        except Exception as exc:
            logger.warning('Could not load recent datasets: %s', exc)
            self.recent_layout.addWidget(QLabel("Error loading recent datasets."))

    def _load_recent_file(self, file_path: str):
        import os
        if not os.path.exists(file_path):
            QMessageBox.warning(self, 'File Not Found', "This file could not be found at its original location. It may have been moved or deleted.")
            return
        self._load_file(file_path)

    def _build_preview_state(self):
        self.preview_widget = QWidget()
        prev_layout = QVBoxLayout(self.preview_widget)
        prev_layout.setContentsMargins(0, 0, 0, 0)
        prev_layout.setSpacing(12)

        # Header Card
        self.info_group = QGroupBox('Dataset Information')
        self.info_group.setStyleSheet(f"QGroupBox {{ padding: 16px; margin-top: 10px; background-color: {PANEL_WHITE}; border: 1px solid {STEEL_LINE}; border-radius: 6px; }}")
        info_layout = QHBoxLayout(self.info_group)
        
        self.file_info_label = QLabel('')
        info_layout.addWidget(self.file_info_label, 1)

        self.proceed_btn = QPushButton('▶  Proceed to Analysis')
        self.proceed_btn.setFixedHeight(48)
        self.proceed_btn.setFixedWidth(200)
        self.proceed_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SIGNAL_BLUE}; font-weight: bold; font-size: 11pt;
            }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
            QPushButton:pressed {{ background-color: #1E3A8A; }}
        """)
        self.proceed_btn.clicked.connect(self._proceed)
        info_layout.addWidget(self.proceed_btn)
        
        prev_layout.addWidget(self.info_group)

        # Preview table (FR-007)
        self.preview_group = QGroupBox(f'Data Preview (first {PREVIEW_ROW_COUNT} rows)')
        self.preview_group.setStyleSheet(f"QGroupBox {{ padding: 16px; margin-top: 10px; background-color: {PANEL_WHITE}; border: 1px solid {STEEL_LINE}; border-radius: 6px; }}")
        preview_layout = QVBoxLayout(self.preview_group)

        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setMouseTracking(True)
        self.preview_table.setStyleSheet("QTableWidget::item:hover { background-color: #EFF6FF; color: #111827; }")
        preview_layout.addWidget(self.preview_table)

        prev_layout.addWidget(self.preview_group, 1)

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

        # Populate preview table (FR-007)
        self._populate_preview(data['dataframe'])
        self.stack.setCurrentWidget(self.preview_widget)

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
        preview = df.head(PREVIEW_ROW_COUNT)
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
