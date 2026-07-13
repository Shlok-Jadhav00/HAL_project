import os

filepath = r'e:\AEIA\gui\history_panel.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '# TODO: Integrate with main window to reload session results',
    '# FUTURE SCOPE (v2.0): Integrate with main window to fully reload session results'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
