filepath = r'e:\AEIA\run_all.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# remove everything after line 88 if it exists
lines = content.split('\n')
if len(lines) > 88:
    content = '\n'.join(lines[:88])
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
