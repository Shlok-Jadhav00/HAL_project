import sys, os, json
sys.path.insert(0, os.path.join(r'e:\AEIA', '.test_output', '..'))

from core import (
    data_loader, preprocessor, statistics_engine, anomaly_detector, 
    expert_system, insight_generator
)

data_path = os.path.join(r'e:\AEIA', 'sample_data', 'aeia_clean_engine_dataset.csv')
rules_path = os.path.join(r'e:\AEIA', 'rules', 'engineering_rules.json')

df, col_types, _ = data_loader.load_dataset(data_path)
di = {'filename': 'aeia_clean_engine_dataset.csv', 'row_count': len(df), 'column_count': len(df.columns)}

df_clean, _ = preprocessor.preprocess_dataset(df, col_types)
mt = {k: v for k, v in col_types.items() if k != 'Sample_ID'}

stats = statistics_engine.compute_statistics(df_clean, mt)
anomalies = anomaly_detector.detect_anomalies(df_clean, mt)
rules = expert_system.load_rules(rules_path)
matches = expert_system.evaluate_rules(rules, stats, anomalies, df=df_clean)

insights = insight_generator.generate_insights(stats, anomalies, matches, di)

output = {
    'anomalies': anomalies,
    'matches': matches,
    'insights': insights['all_insights']
}

with open('clean_analysis.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)

print('Dumped clean_analysis.json')
