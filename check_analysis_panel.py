filepath = r'e:\AEIA\gui\analysis_panel.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure chart_bytes is passed as charts
content = content.replace(
    'charts=chart_bytes,',
    'charts=chart_bytes,'
)
print('Check successful')
