"""Quick pipeline integration test against sample_data/engine_test_run.csv.

Validates Modules 1–9 end-to-end using the actual function signatures.
"""
import sys
import os
import json
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import (
    data_loader, preprocessor, statistics_engine,
    anomaly_detector, expert_system, insight_generator,
    recommendation_engine, chart_builder, report_builder,
)

# Load settings
settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
with open(settings_path, 'r') as f:
    settings = json.load(f)

# ========== Module 1: Load dataset ==========
csv_path = os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'engine_test_run.csv')
df, column_types, file_type = data_loader.load_dataset(csv_path)
print(f"[Module 1] Load: file_type={file_type}, rows={len(df)}, cols={len(df.columns)}")
print(f"  Column types: {column_types}")

# ========== Module 2: Preprocess ==========
df_clean, issues = preprocessor.preprocess_dataset(df, column_types)
print(f"[Module 2] Preprocess: cleaned rows={len(df_clean)}, issues={len(issues)}")
for iss in issues[:5]:
    print(f"  - {iss}")

# ========== Module 3: Statistics ==========
stats = statistics_engine.compute_statistics(df_clean, column_types)
print(f"[Module 3] Statistics: columns={list(stats.get('column_stats', {}).keys())}")
print(f"  Correlations: {len(stats.get('correlations', []))}")

# ========== Module 4: Anomalies ==========
anomalies = anomaly_detector.detect_anomalies(df_clean, column_types)
anom_list = anomalies.get('anomalies', [])
print(f"[Module 4] Anomalies: {len(anom_list)} found")
for a in anom_list[:5]:
    print(f"  - {a.get('column', '?')} row {a.get('row_index', '?')}: {a.get('method', '?')} ({a.get('severity', '?')})")

# ========== Module 5: Expert System ==========
rules_path = os.path.join(os.path.dirname(__file__), '..', 'rules', 'engineering_rules.json')
rules = expert_system.load_rules(rules_path)
rule_results = expert_system.evaluate_rules(rules, stats, anomalies, df_clean)
fired = [r for r in rule_results if r.get('fired')]
print(f"[Module 5] Expert: {len(rule_results)} evaluated, {len(fired)} fired")
for r in fired:
    print(f"  - {r.get('rule_id', '?')}: {r.get('message', 'fired')[:80]}")

# ========== Module 6: Insights ==========
dataset_info = {
    'filename': 'engine_test_run.csv',
    'row_count': len(df),
    'column_count': len(df.columns),
    'import_date': '2026-07-12',
}
insights_result = insight_generator.generate_insights(
    stats, anomalies, rule_results, dataset_info
)
insight_list = insights_result.get('insights', [])
print(f"[Module 6] Insights: {len(insight_list)} generated")
for ins in insight_list[:5]:
    text = ins.get('text', '')
    print(f"  - [{ins.get('severity', 'N/A')}] {text[:80]}")

# ========== Module 7: Recommendations ==========
recs = recommendation_engine.generate_recommendations(insights_result, rule_results)
print(f"[Module 7] Recommendations: {len(recs)} generated")
for r in recs[:3]:
    print(f"  - [{r.get('priority', '?')}] {r.get('text', r.get('recommendation', ''))[:80]}")

conclusion = recommendation_engine.generate_conclusion(insights_result, recs)
print(f"  Conclusion: {conclusion[:100]}...")

# ========== Module 8: Charts ==========
charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, column_types)
print(f"[Module 8] Charts: {len(charts)} generated: {list(charts.keys())}")

# Convert chart figures to bytes for the report
chart_bytes = {}
for name, fig in charts.items():
    chart_bytes[name] = chart_builder.save_figure_to_bytes(fig)
    import matplotlib.pyplot as plt
    plt.close(fig)

# ========== Module 9: Report ==========
report_dir = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(report_dir, exist_ok=True)
output_path = os.path.join(report_dir, 'test_report.pdf')
try:
    result_path = report_builder.generate_pdf_report(
        output_path=output_path,
        dataset_info=dataset_info,
        session_id=1,
        statistics=stats,
        anomalies=anomalies,
        insights=insights_result,
        conclusion=conclusion,
        recommendations=recs,
        charts=chart_bytes,
        include_charts=True,
    )
    print(f"[Module 9] Report: generated -> {result_path}")
except Exception as e:
    print(f"[Module 9] Report FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n=== FULL PIPELINE TEST COMPLETE ===")
