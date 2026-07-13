filepath = r'e:\AEIA\.test_output\generate_final_report.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    \"settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')\",
    \"import json\nsettings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')\"
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
