filepath = r'e:\AEIA\main.py'
with open(filepath, 'rb') as f:
    raw = f.read()

# It might be cp1252
try:
    content = raw.decode('utf-8')
except UnicodeDecodeError:
    content = raw.decode('cp1252')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
