import os
import re

for filepath in [r'e:\AEIA\run_all.py', r'e:\AEIA\.test_output\generate_final_report.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace(
        'raw_charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, mt)\n    charts = {k: chart_builder.save_figure_to_bytes(v) for k, v in raw_charts.items() if v is not None}',
        'charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, mt)'
    )
    
    # Also replace if it was named 'chart_bytes' in generate_final_report.py
    content = content.replace(
        'raw_charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, mt)\nchart_bytes = {k: chart_builder.save_figure_to_bytes(v) for k, v in raw_charts.items() if v is not None}',
        'charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, mt)'
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
