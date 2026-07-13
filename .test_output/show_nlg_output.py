"""Quick script to see current NLG output quality."""
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
conclusion = recommendation_engine.generate_conclusion(insights)
recs = recommendation_engine.generate_recommendations(insights, matches)

print("=== CURRENT CONCLUSION ===")
print(conclusion)
print()
print("=== CURRENT DATASET SUMMARY ===")
print(insights['dataset_summary'])
print()
print("=== ALL INSIGHTS ===")
for i, ins in enumerate(insights['all_insights']):
    sev = ins.get('severity', '?')
    text = ins.get('text', '')
    print(f"  {i+1}. [{sev}] {text}")
print()
print("=== RECOMMENDATIONS ===")
for i, r in enumerate(recs):
    print(f"  {i+1}. {r['text']}")
