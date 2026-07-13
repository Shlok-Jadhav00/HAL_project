import os
import re

filepath = r'e:\AEIA\core\chart_builder.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace return type hint
content = content.replace('-> Dict[str, plt.Figure]:', '-> Dict[str, bytes]:')
content = content.replace('Dict mapping chart_name ? Figure.', 'Dict mapping chart_name ? bytes.')

# Replace appending logic
content = re.sub(
    r'            fig = generate_trend_chart\(df, col, statistics, anomalies\)\n            charts\[f\'trend_\{col\}\'\] = fig',
    '''            fig = generate_trend_chart(df, col, statistics, anomalies)
            if fig is not None:
                charts[f'trend_{col}'] = save_figure_to_bytes(fig)''',
    content
)

content = re.sub(
    r'            fig = generate_histogram\(df, col\)\n            charts\[f\'histogram_\{col\}\'\] = fig',
    '''            fig = generate_histogram(df, col)
            if fig is not None:
                charts[f'histogram_{col}'] = save_figure_to_bytes(fig)''',
    content
)

content = re.sub(
    r'        fig = generate_correlation_heatmap\(statistics\)\n        if fig is not None:\n            charts\[\'correlation_heatmap\'\] = fig',
    '''        fig = generate_correlation_heatmap(statistics)
        if fig is not None:
            charts['correlation_heatmap'] = save_figure_to_bytes(fig)''',
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
