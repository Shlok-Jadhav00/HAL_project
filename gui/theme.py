"""
AEIA — GUI Theme Module

Centralizes all UI colors, fonts, and style constants from
color_philosophy.md. All GUI modules import from here —
never use inline hex codes in panel files.

Colors: color_philosophy.md §The Palette, §Severity Color Mapping,
        §Module Color Identifiers, §Specific UI Component Rules.
Layout: implementation_specification.md §7.
"""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# The Palette (from docs/color_philosophy.md)
# ---------------------------------------------------------------------------

INSTRUMENT_NAVY = '#10243E'
INSTRUMENT_NAVY_QC = QColor(INSTRUMENT_NAVY)

SIGNAL_BLUE = '#2563EB'
SIGNAL_BLUE_QC = QColor(SIGNAL_BLUE)

CONSOLE_GREY = '#F7F8FA'
CONSOLE_GREY_QC = QColor(CONSOLE_GREY)

PANEL_WHITE = '#FFFFFF'
PANEL_WHITE_QC = QColor(PANEL_WHITE)

STEEL_LINE = '#D3D8E0'
STEEL_LINE_QC = QColor(STEEL_LINE)

GRAPHITE = '#111827'
GRAPHITE_QC = QColor(GRAPHITE)

MUTED_SLATE = '#6B7280'
MUTED_SLATE_QC = QColor(MUTED_SLATE)

ALERT_RED = '#DC2626'
ALERT_RED_QC = QColor(ALERT_RED)

CAUTION_AMBER = '#D97706'
CAUTION_AMBER_QC = QColor(CAUTION_AMBER)

INFO_BLUE = '#2563EB'
INFO_BLUE_QC = QColor(INFO_BLUE)

CONFIRMED_GREEN = '#16A34A'
CONFIRMED_GREEN_QC = QColor(CONFIRMED_GREEN)

INFO_BLUE_BG = '#DBEAFE'
INFO_BLUE_TEXT = '#1D4ED8'

# Module Identifiers
MODULE_COLORS = {
    'Import': SIGNAL_BLUE,
    'Preprocess': '#0D9488',
    'Statistics': INSTRUMENT_NAVY,
    'Anomaly': '#4338CA',
    'Rules': '#6D28D9',
    'Findings': GRAPHITE,
    'Report': CONFIRMED_GREEN,
    'History': MUTED_SLATE,
    'Settings': '#7C4A1E',
}


# ---------------------------------------------------------------------------
# Layout constants (implementation_specification.md §7)
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 800

SIDEBAR_WIDTH = 220
SIDEBAR_COLLAPSED_WIDTH = 60
PREVIEW_ROW_COUNT = 20

# Font sizes (§7)
BODY_FONT_SIZE = 10
SECTION_HEADER_FONT_SIZE = 14
PAGE_TITLE_FONT_SIZE = 18


# ---------------------------------------------------------------------------
# Stylesheet generation
# ---------------------------------------------------------------------------

def get_app_stylesheet() -> str:
    """Return the main application stylesheet.

    Uses only colors from color_philosophy.md.
    """
    return f"""
        /* === Global === */
        QWidget {{
            font-family: "Segoe UI", "Inter", "IBM Plex Sans", sans-serif;
            font-size: {BODY_FONT_SIZE}pt;
            color: {GRAPHITE};
            background-color: {CONSOLE_GREY};
        }}

        /* === Main Window === */
        QMainWindow {{
            background-color: {CONSOLE_GREY};
        }}

        /* === Sidebar === */
        #sidebar {{
            background-color: {INSTRUMENT_NAVY};
            min-width: {SIDEBAR_COLLAPSED_WIDTH}px;
            max-width: {SIDEBAR_WIDTH}px;
        }}

        #sidebar QLabel {{
            background-color: transparent;
        }}

        #sidebar QPushButton {{
            background-color: transparent;
            color: white;
            border: none;
            padding: 12px 16px;
            text-align: left;
            font-size: {BODY_FONT_SIZE}pt;
            border-left: 4px solid transparent; /* Reserve space for active indicator */
        }}

        #sidebar QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.08);
        }}

        #sidebar QPushButton:checked,
        #sidebar QPushButton[active="true"] {{
            background-color: {CONSOLE_GREY};
            color: {GRAPHITE};
            border-left: 4px solid {SIGNAL_BLUE};
        }}

        /* === Cards / Panels === */
        .card, QGroupBox {{
            background-color: {PANEL_WHITE};
            border: 1px solid {STEEL_LINE};
            border-radius: 6px;
            padding: 12px;
        }}

        /* === Tables === */
        QTableWidget, QTableView {{
            background-color: {PANEL_WHITE};
            gridline-color: {STEEL_LINE};
            border: 1px solid {STEEL_LINE};
            selection-background-color: {CONSOLE_GREY};
        }}

        QHeaderView::section {{
            background-color: {INSTRUMENT_NAVY};
            color: white;
            padding: 6px;
            border: none;
            font-weight: bold;
        }}

        /* === Buttons === */
        QPushButton {{
            background-color: {SIGNAL_BLUE};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: #1D4ED8;
        }}

        QPushButton:pressed {{
            background-color: #1E40AF;
        }}

        QPushButton:disabled {{
            background-color: {STEEL_LINE};
            color: {MUTED_SLATE};
        }}

        QPushButton#destructive {{
            background-color: {ALERT_RED};
        }}

        QPushButton#destructive:hover {{
            background-color: #B91C1C;
        }}

        /* === Input fields === */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {PANEL_WHITE};
            border: 1px solid {STEEL_LINE};
            border-radius: 4px;
            padding: 6px;
            color: {GRAPHITE};
        }}

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QComboBox:focus {{
            border-color: {SIGNAL_BLUE};
        }}

        /* === Tab Widget === */
        QTabWidget::pane {{
            border: 1px solid {STEEL_LINE};
            background-color: {PANEL_WHITE};
        }}

        QTabBar::tab {{
            background-color: {CONSOLE_GREY};
            border: 1px solid {STEEL_LINE};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
            color: {MUTED_SLATE};
        }}

        QTabBar::tab:selected {{
            background-color: {PANEL_WHITE};
            color: {GRAPHITE};
            border-bottom: 2px solid {SIGNAL_BLUE};
        }}

        /* === Progress Bar === */
        QProgressBar {{
            border: 1px solid {STEEL_LINE};
            border-radius: 4px;
            text-align: center;
            background-color: {CONSOLE_GREY};
        }}

        QProgressBar::chunk {{
            background-color: {SIGNAL_BLUE};
            border-radius: 3px;
        }}

        /* === Status Bar === */
        QStatusBar {{
            background-color: {INSTRUMENT_NAVY};
            color: white;
        }}

        /* === Scroll Bars === */
        QScrollBar:vertical {{
            background-color: {CONSOLE_GREY};
            width: 10px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {STEEL_LINE};
            border-radius: 5px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {MUTED_SLATE};
        }}

        QScrollBar:horizontal {{
            background-color: {CONSOLE_GREY};
            height: 10px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {STEEL_LINE};
            border-radius: 5px;
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {MUTED_SLATE};
        }}

        /* === Labels === */
        QLabel#sectionHeader {{
            font-size: {SECTION_HEADER_FONT_SIZE}pt;
            font-weight: bold;
            color: {GRAPHITE};
        }}

        QLabel#pageTitle {{
            font-size: {PAGE_TITLE_FONT_SIZE}pt;
            font-weight: bold;
            color: {GRAPHITE};
        }}

        QLabel#secondaryText {{
            color: {MUTED_SLATE};
        }}

        /* === Severity badges === */
        QLabel#severityCritical {{
            background-color: #FEE2E2;
            color: {ALERT_RED};
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
        }}

        QLabel#severityWarning {{
            background-color: #FEF3C7;
            color: {CAUTION_AMBER};
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
        }}

        QLabel#severityInfo {{
            background-color: {INFO_BLUE_BG};
            color: {INFO_BLUE_TEXT};
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: bold;
        }}
    """


def apply_theme(app: QApplication) -> None:
    """Apply the AEIA theme to the application.

    Call this once in main.py after creating the QApplication instance.
    """
    app.setStyleSheet(get_app_stylesheet())

SEVERITY_COLORS = {
    'Critical': ALERT_RED,
    'Warning': CAUTION_AMBER,
    'Info': INFO_BLUE,
}

SEVERITY_BG_COLORS = {
    'Critical': '#FEE2E2', # As per docs
    'Warning': '#FEF3C7',
    'Info': INFO_BLUE_BG,
}

SEVERITY_TEXT_COLORS = {
    'Critical': ALERT_RED,
    'Warning': CAUTION_AMBER,
    'Info': INFO_BLUE_TEXT,
}
