filepath = r'e:\AEIA\core\config_manager.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\"', '"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
