import os
import re

filepath = r'e:\AEIA\gui\main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '            icon_path = os.path.join(\n                os.path.join(os.path.dirname(os.path.dirname(__file__)),\n                             \'gui\', \'assets\', \'icon.png\')\n            )',
    '            from core.config_manager import resource_path\n            icon_path = resource_path(\'gui/assets/icon.png\')'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
