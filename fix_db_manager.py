import os
import re

filepath = r'e:\AEIA\database\db_manager.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '        schema_path = os.path.join(\n                os.path.dirname(os.path.abspath(__file__)), \'schema.sql\'\n            )',
    '        from core.config_manager import resource_path\n        schema_path = resource_path(\'database/schema.sql\')'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
