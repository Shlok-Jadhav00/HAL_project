"""
AEIA — GUI Table Models

Provides QAbstractTableModel implementations for massive datasets to ensure
GUI virtualization (Phase 5 Performance Optimization).
"""

from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from typing import List, Dict, Any, Tuple

from gui.theme import MUTED_SLATE, PANEL_WHITE


class HistoryTableModel(QAbstractTableModel):
    """Model for the Sessions History table."""
    def __init__(self, data: List[Dict[str, Any]] = None):
        super().__init__()
        self._data = data or []
        self._headers = ["Session ID", "Dataset", "Started", "Status", "Findings"]

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()
        item = self._data[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return str(item.get('session_id', ''))
            elif col == 1:
                return str(item.get('dataset_name', ''))
            elif col == 2:
                return str(item.get('started_on', ''))
            elif col == 3:
                return str(item.get('status', ''))
            elif col == 4:
                return str(item.get('findings_count', '0'))
        
        elif role == Qt.TextAlignmentRole:
            if col in (0, 4):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter
            
        elif role == Qt.ForegroundRole:
            if col == 3:
                status = item.get('status', '')
                if status == 'Completed':
                    from PyQt5.QtGui import QColor
                    return QColor('#16A34A')  # CONFIRMED_GREEN
                elif status == 'Failed':
                    from PyQt5.QtGui import QColor
                    return QColor('#DC2626')  # ALERT_RED

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return QVariant()

    def get_session_id(self, row: int) -> int:
        if 0 <= row < len(self._data):
            return self._data[row].get('session_id', -1)
        return -1


class AnomalyTableModel(QAbstractTableModel):
    """Model for the Anomalies table."""
    def __init__(self, data: List[Dict[str, Any]] = None):
        super().__init__()
        self._data = data or []
        self._headers = ["Column", "Row", "Method", "Severity", "Value", "Actions"]

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()
        item = self._data[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return str(item.get('column_name', ''))
            elif col == 1:
                return str(item.get('row_reference', ''))
            elif col == 2:
                return str(item.get('method', ''))
            elif col == 3:
                return str(item.get('severity', ''))
            elif col == 4:
                val = item.get('value')
                if val is not None:
                    return f"{val:.4f}" if isinstance(val, float) else str(val)
                return "N/A"
            elif col == 5:
                return "[ Mark FP ]"
                
        elif role == Qt.TextAlignmentRole:
            if col in (1, 4):
                return Qt.AlignRight | Qt.AlignVCenter
            elif col == 5:
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter
            
        elif role == Qt.ForegroundRole:
            if col == 3:
                sev = item.get('severity', '')
                from PyQt5.QtGui import QColor
                if sev == 'Critical':
                    return QColor('#DC2626')
                elif sev == 'Warning':
                    return QColor('#D97706')
                elif sev == 'Info':
                    return QColor('#2563EB')
            elif col == 5:
                from PyQt5.QtGui import QColor
                return QColor('#6B7280') # MUTED_SLATE

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return QVariant()

    def get_anomaly_info(self, row: int) -> Tuple[str, int]:
        if 0 <= row < len(self._data):
            col = self._data[row].get('column_name', '')
            row_ref = self._data[row].get('row_reference', -1)
            return col, row_ref
        return "", -1
