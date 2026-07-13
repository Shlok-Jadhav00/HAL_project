import os
import re

filepath = r'e:\AEIA\core\data_loader.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'parsed = pd.to_datetime(non_null)',
    'parsed = pd.to_datetime(non_null, format=\'mixed\')'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
