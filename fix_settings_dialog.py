import os
import re

filepath = r'e:\AEIA\gui\settings_dialog.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _find_settings_path
content = re.sub(
    r'    def _find_settings_path\(self\) -> str:.*?        return os\.path\.join\(base, \'config\', \'settings\.json\'\)',
    '''    def _find_settings_path(self) -> str:
        \"\"\"Find the settings.json path.\"\"\"
        from core.config_manager import get_settings_path
        return get_settings_path()''',
    content,
    flags=re.DOTALL
)

# Replace _load_settings to use config_manager
content = re.sub(
    r'    def _load_settings\(self\):.*?            self\.settings = {}',
    '''    def _load_settings(self):
        \"\"\"Load settings from JSON file (FR-095).\"\"\"
        from core.config_manager import load_settings
        self.settings = load_settings()''',
    content,
    flags=re.DOTALL
)

# Replace rule path logic in _load_rules_table
content = re.sub(
    r'            rules_path = os\.path\.join\([\s\S]*?            with open\(rules_path, \'r\', encoding=\'utf-8\'\) as f:',
    '''            from core.config_manager import get_rules_path
            rules_path = get_rules_path()
            with open(rules_path, 'r', encoding='utf-8') as f:''',
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
