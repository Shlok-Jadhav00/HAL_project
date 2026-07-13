"""Test the new Executive Summary Composer output."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import data_loader, preprocessor, statistics_engine, anomaly_detector, expert_system, insight_generator, recommendation_engine

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

# NEW: Test the executive summary composer directly
from core.executive_summary_composer import compose_executive_summary, humanize_column_name

print("=== COLUMN HUMANIZATION TESTS ===")
test_cols = ['Engine_Temp_C', 'Oil_Pressure_psi', 'RPM', 'Vibration_mm_s', 'Sample_ID', 'Status']
for col in test_cols:
    print(f"  {col} -> {humanize_column_name(col)}")

print()
print("=== NEW EXECUTIVE SUMMARY ===")
result = compose_executive_summary(insights, statistics=stats, dataset_info=di)
print(result['text'])

print()
print("=== TRACEABILITY ===")
for i, para in enumerate(result['paragraphs']):
    sources = para.get('source_findings', [])
    cat = para.get('narrative_category', '?')
    src_summary = ', '.join(f"{s['finding_type']}" for s in sources[:3])
    if len(sources) > 3:
        src_summary += f" (+{len(sources)-3} more)"
    print(f"  Para {i+1} [{cat}]: {len(sources)} source(s) -> {src_summary}")

print()
print("=== BACKWARD COMPAT: generate_conclusion() ===")
conclusion = recommendation_engine.generate_conclusion(insights)
print(conclusion[:200] + "..." if len(conclusion) > 200 else conclusion)
