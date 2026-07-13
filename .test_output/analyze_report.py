import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import data_loader, preprocessor, statistics_engine, anomaly_detector, expert_system, insight_generator, recommendation_engine

# Load Data
df, col_types, _ = data_loader.load_dataset(
    os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'engine_test_run.csv')
)
df_clean, _ = preprocessor.preprocess_dataset(df, col_types)
mt = {k: v for k, v in col_types.items() if k != 'Sample_ID'}
stats = statistics_engine.compute_statistics(df_clean, mt)
anomalies = anomaly_detector.detect_anomalies(df_clean, mt)
rules = expert_system.load_rules(
    os.path.join(os.path.dirname(__file__), '..', 'rules', 'engineering_rules.json')
)
matches = expert_system.evaluate_rules(rules, stats, anomalies, df=df_clean)
di = {'filename': 'engine_test_run.csv', 'row_count': 61, 'column_count': 7, 'import_date': '2026-07-12'}
insights = insight_generator.generate_insights(stats, anomalies, matches, di)

print("=== OLD EXECUTIVE SUMMARY ===")
severity_counts = recommendation_engine._count_severities(insights['all_insights'])
total = len(insights['all_insights'])
parts = [f"Analysis identified {total} finding(s) across the dataset."]
if severity_counts.get('Critical', 0) > 0:
    parts.append(f"{severity_counts['Critical']} Critical finding(s) require immediate attention.")
if severity_counts.get('Warning', 0) > 0:
    parts.append(f"{severity_counts['Warning']} Warning-level finding(s) were detected.")
if severity_counts.get('Info', 0) > 0:
    parts.append(f"{severity_counts['Info']} informational finding(s) noted.")
print(' '.join(parts))

print("\n=== NEW EXECUTIVE SUMMARY (WITH TRACEABILITY) ===")
from core.executive_summary_composer import compose_executive_summary
result = compose_executive_summary(insights, statistics=stats, dataset_info=di)
for i, para in enumerate(result['paragraphs']):
    print(f"\n[Paragraph {i+1}]")
    print(f"TEXT: {para['text']}")
    print(f"SOURCES: {para.get('source_findings', [])}")

print("\n=== DETAILED FINDINGS SECTION EXAMPLES ===")
for i, finding in enumerate(insights['all_insights'][:5]):
    print(f"- {finding['column']} ({finding['finding_type']}): {finding['text']}")

