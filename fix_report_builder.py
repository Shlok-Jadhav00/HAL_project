import os
import re

filepath = r'e:\AEIA\core\report_builder.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''# Colors from color_philosophy.md
from core import color_palette as cp
INSTRUMENT_NAVY = colors.HexColor(cp.INSTRUMENT_NAVY)
SIGNAL_BLUE = colors.HexColor(cp.SIGNAL_BLUE)
ALERT_RED = colors.HexColor(cp.ALERT_RED)
CAUTION_AMBER = colors.HexColor(cp.CAUTION_AMBER)
INFO_BLUE = colors.HexColor(cp.INFO_BLUE)
GRAPHITE = colors.HexColor(cp.GRAPHITE)
STEEL_LINE = colors.HexColor(cp.STEEL_LINE)
CONSOLE_GREY = colors.HexColor(cp.CONSOLE_GREY)
PANEL_WHITE = colors.white'''

content = re.sub(
    r'# Colors from color_philosophy\.md\nINSTRUMENT_NAVY = [^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\nPANEL_WHITE = colors\.white',
    replacement,
    content,
    flags=re.MULTILINE
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
