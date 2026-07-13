import os
import re

filepath = r'e:\AEIA\gui\analysis_panel.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace manual settings loading in run()
content = re.sub(
    r'            settings_path = os\.path\.join\([\s\S]*?            stat_cfg = settings\.get\(\'statistics\', \{\}\)',
    '''            from core.config_manager import load_settings, get_rules_path
            settings = load_settings()
            det_cfg = settings.get('detection', {})
            stat_cfg = settings.get('statistics', {})''',
    content
)

# Replace rule path logic
content = re.sub(
    r'            rules_path = os\.path\.join\([\s\S]*?            rules = load_rules\(rules_path\)',
    '''            rules_path = get_rules_path()
            rules = load_rules(rules_path)''',
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
