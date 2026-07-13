import os
filepath = r'e:\AEIA\core\insight_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix raw_severity reference
content = content.replace(
    \"any(r.get('raw_severity') == 'Critical' for r in rule_detectors)\",
    \"any(r.get('severity') == 'Critical' for r in rule_detectors)\"
)

content = content.replace(
    \"if insight.get('raw_severity') == 'Critical' and insight.get('source_type') == 'Rule':\",
    \"if insight.get('severity') == 'Critical' and insight.get('source_type') == 'Rule':\"
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
