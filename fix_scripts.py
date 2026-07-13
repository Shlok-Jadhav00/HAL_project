import os
import re

for filepath in [r'e:\AEIA\run_all.py', r'e:\AEIA\.test_output\generate_final_report.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace manual settings loading
    content = re.sub(
        r'import json\nsettings_path = os\.path\.join\([\s\S]*?stat_cfg = settings\.get\(\'statistics\', \{\}\)',
        '''from core.config_manager import load_settings, get_rules_path
settings = load_settings()
det_cfg = settings.get('detection', {})
stat_cfg = settings.get('statistics', {})''',
        content
    )

    # Replace rule path logic
    content = re.sub(
        r'rules_path = os\.path\.join\(.*?, \'rules\', \'engineering_rules\.json\'\)',
        '''rules_path = get_rules_path()''',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
