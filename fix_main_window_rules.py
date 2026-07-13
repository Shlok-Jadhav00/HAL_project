import os
import re

filepath = r'e:\AEIA\gui\main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''            rules_path = self.session_data.get(
                'rules_path',
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'rules', 'engineering_rules.json')
            )''',
    '''            from core.config_manager import get_rules_path
            rules_path = self.session_data.get('rules_path') or get_rules_path()'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
