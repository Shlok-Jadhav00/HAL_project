import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import (
    data_loader, preprocessor, statistics_engine, anomaly_detector, 
    expert_system, insight_generator, recommendation_engine, chart_builder, report_builder
)

# Configuration
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample_data', 'engine_test_run.csv'))
rules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'rules', 'engineering_rules.json'))
output_dir = os.path.abspath(os.path.join(os.environ.get('APPDATA', ''), '..', 'Local', 'Temp', 'AEIA_Reports'))

if not os.path.exists(output_dir):
    os.makedirs(output_dir)
output_path = os.path.join(output_dir, 'engine_test_run_report.pdf')

from core.config_manager import load_settings, get_rules_path
settings = load_settings()
det_cfg = settings.get('detection', {})
stat_cfg = settings.get('statistics', {})

# 1. Load Data
df, col_types, _ = data_loader.load_dataset(data_path)
di = {'filename': 'engine_test_run.csv', 'row_count': 61, 'column_count': 7, 'import_date': '2026-07-13'}

# 2. Preprocess
df_clean, _ = preprocessor.preprocess_dataset(df, col_types)
mt = {k: v for k, v in col_types.items() if k != 'Sample_ID'}

# 3. Analyze
stats = statistics_engine.compute_statistics(
    df_clean, mt,
    correlation_threshold=stat_cfg.get('correlation_threshold', 0.7),
    trend_window_fraction=stat_cfg.get('trend_window_fraction_of_dataset', 0.1),
    trend_window_min=stat_cfg.get('trend_window_min_samples', 3),
    trend_window_max=stat_cfg.get('trend_window_max_samples', 20),
    trend_stability_multiplier=stat_cfg.get('trend_stability_std_multiplier', 0.5),
    trend_minimum_slope_magnitude=stat_cfg.get('trend_minimum_slope_magnitude', 0.01)
)
anomalies = anomaly_detector.detect_anomalies(
    df_clean, mt,
    zscore_threshold=det_cfg.get('zscore_threshold', 3.0),
    iqr_multiplier=det_cfg.get('iqr_multiplier', 1.5),
    if_contamination=det_cfg.get('isolation_forest_contamination', 0.05),
    if_n_estimators=det_cfg.get('isolation_forest_n_estimators', 100),
    if_random_state=det_cfg.get('isolation_forest_random_state', 42)
)

# 4. Expert System
rules = expert_system.load_rules(rules_path)
matches = expert_system.evaluate_rules(rules, stats, anomalies, df=df_clean)

# 5. Insights & Conclusion
insights = insight_generator.generate_insights(stats, anomalies, matches, di)
recommendations = recommendation_engine.generate_recommendations(insights, matches)
conclusion = recommendation_engine.generate_conclusion(insights, statistics=stats, dataset_info=di)

# 6. Charts
raw_charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, mt)
charts = {k: chart_builder.save_figure_to_bytes(v) for k, v in raw_charts.items() if v is not None}

# 7. Generate PDF
report_builder.generate_pdf_report(
    output_path=output_path,
    dataset_info=di,
    session_id=1,
    statistics=stats,
    anomalies=anomalies,
    insights=insights,
    conclusion=conclusion,
    recommendations=recommendations,
    charts=charts,
    include_charts=True
)

print(f"PDF generated successfully at: {output_path}")
