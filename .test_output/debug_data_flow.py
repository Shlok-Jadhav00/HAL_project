"""Inspect data structures from Module 3-5 to debug rule firing."""
import sys
import os
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import data_loader, preprocessor, statistics_engine, anomaly_detector, expert_system

df, col_types, ftype = data_loader.load_dataset(
    os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'engine_test_run.csv')
)
df_clean, issues = preprocessor.preprocess_dataset(df, col_types)
stats = statistics_engine.compute_statistics(df_clean, col_types)
anomalies = anomaly_detector.detect_anomalies(df_clean, col_types)

# Print stats structure
print("=== STATS TOP-LEVEL KEYS:", list(stats.keys()))
print("=== PER_COLUMN KEYS:", list(stats.get('per_column', {}).keys()))

for col, cstats in stats.get('per_column', {}).items():
    mean = cstats.get('mean')
    std = cstats.get('std_dev')
    slope = cstats.get('trend_slope')
    cv = abs(std / mean) if mean and std and mean != 0 else None
    print(f"  {col}: mean={mean}, std_dev={std}, trend_slope={slope}, CV={cv}")

# Correlations
corr_data = stats.get('correlations', {})
print("\n=== CORRELATIONS KEYS:", list(corr_data.keys()) if isinstance(corr_data, dict) else type(corr_data))
strong = corr_data.get('strong_pairs', []) if isinstance(corr_data, dict) else []
print(f"  Strong pairs: {len(strong)}")
for p in strong:
    print(f"    {p}")

# Anomaly structure
print("\n=== ANOMALY TOP-LEVEL KEYS:", list(anomalies.keys()))
for a in anomalies.get('anomalies', []):
    print(f"  anomaly: col={a.get('column_name','?')}, method={a.get('method','?')}, "
          f"severity={a.get('severity','?')}, row={a.get('row_index','?')}, value={a.get('value','?')}")

print("\n=== IF FLAGS:", list(anomalies.get('isolation_forest_flags', {}).keys())[:10]
      if isinstance(anomalies.get('isolation_forest_flags'), dict) else
      type(anomalies.get('isolation_forest_flags', 'NOT PRESENT')))

# Test Engine_Temp max
print(f"\n=== Engine_Temp_C max: {df_clean['Engine_Temp_C'].max()}")
print(f"=== Values > 120: {df_clean[df_clean['Engine_Temp_C'] > 120]['Engine_Temp_C'].tolist()}")

# Now run expert system
rules = expert_system.load_rules(
    os.path.join(os.path.dirname(__file__), '..', 'rules', 'engineering_rules.json')
)
print(f"\n=== Loaded {len(rules)} rules")
matches = expert_system.evaluate_rules(rules, stats, anomalies, df_clean)
print(f"=== {len(matches)} rules fired")
for m in matches:
    print(f"  FIRED: {m.get('rule_id')} on {m.get('column')} -> {m.get('matched_on')}")
