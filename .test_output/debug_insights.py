"""Debug: why does insight generator produce 0 insights?"""
import sys
import os
import json
import io
import logging

logging.basicConfig(level=logging.DEBUG)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import data_loader, preprocessor, statistics_engine, anomaly_detector, expert_system, insight_generator

df, col_types, ftype = data_loader.load_dataset(
    os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'engine_test_run.csv')
)
df_clean, issues = preprocessor.preprocess_dataset(df, col_types)
stats = statistics_engine.compute_statistics(df_clean, col_types)
anomalies = anomaly_detector.detect_anomalies(df_clean, col_types)
rules = expert_system.load_rules(
    os.path.join(os.path.dirname(__file__), '..', 'rules', 'engineering_rules.json')
)
rule_matches = expert_system.evaluate_rules(rules, stats, anomalies, df_clean)

dataset_info = {
    'filename': 'engine_test_run.csv',
    'row_count': len(df),
    'column_count': len(df.columns),
    'import_date': '2026-07-12',
}

# Check: what does _format_anomaly return for our anomalies?
print("=== ANOMALY DETAILS ===")
for a in anomalies['anomalies']:
    print(f"  {a}")

# Manually test formatting
print("\n=== FORMAT ANOMALY TEST ===")
for a in anomalies['anomalies']:
    try:
        text = insight_generator._format_anomaly(a)
        print(f"  OK: {text[:80] if text else 'None returned'}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Now run full pipeline
print("\n=== GENERATE INSIGHTS ===")
result = insight_generator.generate_insights(stats, anomalies, rule_matches, dataset_info)
print(f"  dataset_summary: {result.get('dataset_summary', 'MISSING')}")
print(f"  anomaly_insights: {len(result.get('anomaly_insights', []))}")
print(f"  pattern_insights: {len(result.get('pattern_insights', []))}")
print(f"  rule_insights: {len(result.get('rule_insights', []))}")
print(f"  all_insights: {len(result.get('all_insights', []))}")

# Print what the recommendation engine sees
print("\n=== WHAT RECOMMENDATION ENGINE GETS ===")
print(f"  insights key 'insights': {type(result.get('insights', 'MISSING'))}")
print(f"  insights key 'all_insights': {type(result.get('all_insights', 'MISSING'))}")
