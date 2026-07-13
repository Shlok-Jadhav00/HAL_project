filepath = r'e:\AEIA\core\color_palette.py'
with open(filepath, 'rb') as f:
    raw = f.read()

try:
    content = raw.decode('utf-8')
except UnicodeDecodeError:
    content = raw.decode('cp1252')

content = content.replace('\\"', '"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
