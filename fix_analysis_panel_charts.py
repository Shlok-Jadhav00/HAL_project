import os
import re

filepath = r'e:\AEIA\gui\analysis_panel.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''            self.progress.emit(95, 'Generating graphs...')
            charts = generate_all_charts(df_clean, stats, anomalies, measurement_types)
            chart_bytes = {name: save_figure_to_bytes(fig) for name, fig in charts.items() if fig is not None}''',
    '''            self.progress.emit(95, 'Generating graphs...')
            chart_bytes = generate_all_charts(df_clean, stats, anomalies, measurement_types)'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
