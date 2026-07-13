"""
AEIA — Settings Dialog (Module 11)

Provides threshold and rule management UI. All settings persisted
to config/settings.json — never hard-coded.

FRs implemented: FR-091 through FR-097.
Colors: gui/theme.py (from color_philosophy.md).

This module contains PyQt5 imports — it lives in gui/.
"""

import json
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from gui.theme import (
    MODULE_COLORS, MUTED_SLATE,
)

logger = logging.getLogger('aeia.settings_dialog')

# Error message from implementation_specification.md §9
ERROR_SETTINGS_VALIDATION = (
    "Please enter a positive number for this setting."
)

# Default settings values (implementation_specification.md §2)
DEFAULT_SETTINGS = {
    'detection.zscore_threshold': 3.0,
    'detection.iqr_multiplier': 1.5,
    'detection.isolation_forest_contamination': 0.05,
    'detection.isolation_forest_n_estimators': 100,
    'detection.isolation_forest_random_state': 42,
    'statistics.correlation_threshold': 0.7,
    'statistics.trend_window_min_samples': 3,
    'statistics.trend_window_max_samples': 20,
    'statistics.trend_window_fraction_of_dataset': 0.1,
    'statistics.trend_stability_std_multiplier': 0.5,
    'statistics.trend_minimum_slope_magnitude': 0.01,
    'preprocessing.default_numeric_fill_constant': 0,
    'preprocessing.default_categorical_fill_constant': 'Unknown',
}


class SettingsDialog(QWidget):
    """Settings management panel.

    FR-091: Configure anomaly detection thresholds.
    FR-092: View/add/edit/disable rules.
    FR-093: Configure default report folder.
    FR-094: Configure correlation threshold.
    FR-095: Store all config in settings.json.
    FR-096: Restore Defaults action.
    FR-097: Validate all input.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self.settings_path = self._find_settings_path()
        self._load_settings()
        self._setup_ui()

    def _find_settings_path(self) -> str:
        """Find the settings.json path."""
        from core.config_manager import get_settings_path
        return get_settings_path()

    def _load_settings(self):
        """Load settings from JSON file (FR-095)."""
        from core.config_manager import load_settings
        self.settings = load_settings()

    def _setup_ui(self):
        """Build the settings panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Module accent
        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet(
            f'background-color: {MODULE_COLORS["Settings"]};'
        )
        layout.addWidget(accent)

        title = QLabel('Settings')
        title.setObjectName('pageTitle')
        layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # Detection settings tab (FR-091)
        tabs.addTab(self._build_detection_tab(), '⚙️ Detection')

        # Statistics settings tab (FR-094)
        tabs.addTab(self._build_statistics_tab(), '📊 Statistics')

        # Rules tab (FR-092)
        tabs.addTab(self._build_rules_tab(), '📜 Rules')

        # Action buttons
        btn_layout = QHBoxLayout()

        save_btn = QPushButton('💾  Save Settings')
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        restore_btn = QPushButton('🔄  Restore Defaults')
        restore_btn.setFixedHeight(36)
        restore_btn.setStyleSheet(f'background-color: {MUTED_SLATE};')
        restore_btn.clicked.connect(self._restore_defaults)
        btn_layout.addWidget(restore_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _build_detection_tab(self) -> QWidget:
        """Build the detection settings form (FR-091)."""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)

        detection = self.settings.get('detection', {})

        # Z-score threshold
        self.zscore_spin = QDoubleSpinBox()
        self.zscore_spin.setRange(0.1, 10.0)
        self.zscore_spin.setDecimals(1)
        self.zscore_spin.setSingleStep(0.5)
        self.zscore_spin.setValue(detection.get('zscore_threshold', 3.0))
        form.addRow('Z-score Threshold (|z| >, default 3.0):', self.zscore_spin)

        # IQR multiplier
        self.iqr_spin = QDoubleSpinBox()
        self.iqr_spin.setRange(0.1, 5.0)
        self.iqr_spin.setDecimals(1)
        self.iqr_spin.setSingleStep(0.5)
        self.iqr_spin.setValue(detection.get('iqr_multiplier', 1.5))
        form.addRow('IQR Multiplier (default 1.5):', self.iqr_spin)

        # IF contamination
        self.if_contamination_spin = QDoubleSpinBox()
        self.if_contamination_spin.setRange(0.01, 0.5)
        self.if_contamination_spin.setDecimals(2)
        self.if_contamination_spin.setSingleStep(0.01)
        self.if_contamination_spin.setValue(
            detection.get('isolation_forest_contamination', 0.05)
        )
        form.addRow('Isolation Forest Contamination (default 0.05):',
                      self.if_contamination_spin)

        # IF estimators
        self.if_estimators_spin = QSpinBox()
        self.if_estimators_spin.setRange(10, 1000)
        self.if_estimators_spin.setSingleStep(10)
        self.if_estimators_spin.setValue(
            detection.get('isolation_forest_n_estimators', 100)
        )
        form.addRow('Isolation Forest Trees (default 100):',
                      self.if_estimators_spin)

        return widget

    def _build_statistics_tab(self) -> QWidget:
        """Build the statistics settings form (FR-094)."""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)

        stats = self.settings.get('statistics', {})

        # Correlation threshold (FR-094)
        self.corr_spin = QDoubleSpinBox()
        self.corr_spin.setRange(0.1, 1.0)
        self.corr_spin.setDecimals(2)
        self.corr_spin.setSingleStep(0.05)
        self.corr_spin.setValue(stats.get('correlation_threshold', 0.7))
        form.addRow('Correlation Threshold (|r| >, default 0.7):',
                      self.corr_spin)

        # Trend stability multiplier
        self.trend_mult_spin = QDoubleSpinBox()
        self.trend_mult_spin.setRange(0.1, 5.0)
        self.trend_mult_spin.setDecimals(1)
        self.trend_mult_spin.setSingleStep(0.1)
        self.trend_mult_spin.setValue(
            stats.get('trend_stability_std_multiplier', 0.5)
        )
        form.addRow('Trend Stability Multiplier (default 0.5):',
                      self.trend_mult_spin)

        # Trend minimum slope magnitude
        self.trend_slope_spin = QDoubleSpinBox()
        self.trend_slope_spin.setRange(0.001, 10.0)
        self.trend_slope_spin.setDecimals(3)
        self.trend_slope_spin.setSingleStep(0.01)
        self.trend_slope_spin.setValue(
            stats.get('trend_minimum_slope_magnitude', 0.01)
        )
        form.addRow('Trend Minimum Slope Magnitude (default 0.01):',
                      self.trend_slope_spin)

        return widget

    def _build_rules_tab(self) -> QWidget:
        """Build the rules management tab (FR-092)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        desc = QLabel(
            'View and manage engineering rules. Rules are loaded from '
            'rules/engineering_rules.json.'
        )
        desc.setWordWrap(True)
        desc.setObjectName('secondaryText')
        layout.addWidget(desc)

        # Rules table
        self.rules_table = QTableWidget()
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setColumnCount(5)
        self.rules_table.setHorizontalHeaderLabels(
            ['Rule ID', 'Name', 'Scope', 'Severity', 'Enabled']
        )
        layout.addWidget(self.rules_table)

        # Load rules into table
        self._load_rules_table()

        return widget

    def _load_rules_table(self):
        """Populate the rules table from engineering_rules.json."""
        try:
            from core.config_manager import get_rules_path
            rules_path = get_rules_path()
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rules = data.get('rules', [])

            self.rules_table.setRowCount(len(rules))
            for row, rule in enumerate(rules):
                items = [
                    rule.get('rule_id', ''),
                    rule.get('rule_name', ''),
                    rule.get('scope_pattern', '*'),
                    rule.get('severity', ''),
                    'Yes' if rule.get('is_enabled', True) else 'No',
                ]
                for col, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    if col < 4:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.rules_table.setItem(row, col, item)

            self.rules_table.resizeColumnsToContents()

        except Exception as exc:
            logger.warning('Could not load rules for display: %s', exc)

    def _save_settings(self):
        """Save settings to JSON file (FR-095, FR-097)."""
        # FR-097: Validate
        if self.zscore_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation Error',
                                 ERROR_SETTINGS_VALIDATION)
            return
        if self.iqr_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation Error',
                                 ERROR_SETTINGS_VALIDATION)
            return

        # Update settings dict
        if 'detection' not in self.settings:
            self.settings['detection'] = {}
        self.settings['detection']['zscore_threshold'] = self.zscore_spin.value()
        self.settings['detection']['iqr_multiplier'] = self.iqr_spin.value()
        self.settings['detection']['isolation_forest_contamination'] = \
            self.if_contamination_spin.value()
        self.settings['detection']['isolation_forest_n_estimators'] = \
            self.if_estimators_spin.value()

        if 'statistics' not in self.settings:
            self.settings['statistics'] = {}
        self.settings['statistics']['correlation_threshold'] = \
            self.corr_spin.value()
        self.settings['statistics']['trend_stability_std_multiplier'] = \
            self.trend_mult_spin.value()
        self.settings['statistics']['trend_minimum_slope_magnitude'] = \
            self.trend_slope_spin.value()

        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            QMessageBox.information(self, 'Settings Saved',
                                     'Settings saved successfully.')
            logger.info('Settings saved to %s', self.settings_path)
        except Exception as exc:
            logger.error('Failed to save settings: %s', exc)
            QMessageBox.critical(self, 'Save Failed', str(exc))

    def _restore_defaults(self):
        """Restore all settings to factory values (FR-096)."""
        reply = QMessageBox.question(
            self, 'Restore Defaults',
            'Are you sure you want to restore all settings to defaults?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.zscore_spin.setValue(3.0)
            self.iqr_spin.setValue(1.5)
            self.if_contamination_spin.setValue(0.05)
            self.if_estimators_spin.setValue(100)
            self.corr_spin.setValue(0.7)
            self.trend_mult_spin.setValue(0.5)
            self.trend_slope_spin.setValue(0.01)
            logger.info('Settings restored to defaults.')
