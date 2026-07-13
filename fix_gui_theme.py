import os

filepath = r'e:\AEIA\gui\theme.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication

from core import color_palette as cp

# ---------------------------------------------------------------------------
# The Palette
# ---------------------------------------------------------------------------

INSTRUMENT_NAVY = cp.INSTRUMENT_NAVY
INSTRUMENT_NAVY_QC = QColor(INSTRUMENT_NAVY)

SIGNAL_BLUE = cp.SIGNAL_BLUE
SIGNAL_BLUE_QC = QColor(SIGNAL_BLUE)

CONSOLE_GREY = cp.CONSOLE_GREY
CONSOLE_GREY_QC = QColor(CONSOLE_GREY)

PANEL_WHITE = cp.PANEL_WHITE
PANEL_WHITE_QC = QColor(PANEL_WHITE)

STEEL_LINE = cp.STEEL_LINE
STEEL_LINE_QC = QColor(STEEL_LINE)

GRAPHITE = cp.GRAPHITE
GRAPHITE_QC = QColor(GRAPHITE)

ALERT_RED = cp.ALERT_RED
ALERT_RED_QC = QColor(ALERT_RED)

CAUTION_AMBER = cp.CAUTION_AMBER
CAUTION_AMBER_QC = QColor(CAUTION_AMBER)

INFO_BLUE = cp.INFO_BLUE
INFO_BLUE_QC = QColor(INFO_BLUE)

CONFIRMED_GREEN = cp.CONFIRMED_GREEN
CONFIRMED_GREEN_QC = QColor(CONFIRMED_GREEN)

MUTED_SLATE = cp.MUTED_SLATE
MUTED_SLATE_QC = QColor(MUTED_SLATE)

INFO_BLUE_BG = cp.INFO_BLUE_BG
INFO_BLUE_TEXT = cp.INFO_BLUE_TEXT

MODULE_COLORS = cp.MODULE_COLORS'''

import re
content = re.sub(
    r'from PyQt5\.QtGui import QColor.*MODULE_COLORS = \{\n[^\}]+\n\}',
    replacement,
    content,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
