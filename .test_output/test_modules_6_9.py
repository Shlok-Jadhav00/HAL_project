"""Test Modules 6-9 with correct data structures."""
import sys
import os
import json
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import (
    data_loader, preprocessor, statistics_engine,
    anomaly_detector, expert_system, insight_generator,
    recommendation_engine, chart_builder, report_builder,
)

# Load + preprocess + stats + anomalies (known working)
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

print(f"Pipeline up to Module 5 OK: {len(rule_matches)} rules fired\n")

# ========== Module 6: Insights ==========
dataset_info = {
    'filename': 'engine_test_run.csv',
    'row_count': len(df),
    'column_count': len(df.columns),
    'import_date': '2026-07-12',
}
try:
    insights_result = insight_generator.generate_insights(
        stats, anomalies, rule_matches, dataset_info
    )
    insight_list = insights_result.get('insights', [])
    print(f"[Module 6] Insights: {len(insight_list)} generated")
    for ins in insight_list[:5]:
        text = ins.get('text', '')
        print(f"  - [{ins.get('severity', 'N/A')}] {text[:100]}")
    if len(insight_list) > 5:
        print(f"  ... and {len(insight_list) - 5} more")
except Exception as e:
    print(f"[Module 6] FAILED: {e}")
    import traceback
    traceback.print_exc()

# ========== Module 7: Recommendations ==========
try:
    recs = recommendation_engine.generate_recommendations(insights_result, rule_matches)
    print(f"\n[Module 7] Recommendations: {len(recs)} generated")
    for r in recs[:5]:
        print(f"  - [{r.get('priority', '?')}] {r.get('text', r.get('recommendation', ''))[:100]}")
except Exception as e:
    print(f"[Module 7] generate_recommendations FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    import inspect
    sig = inspect.signature(recommendation_engine.generate_conclusion)
    print(f"\n  generate_conclusion signature: {sig}")
    conclusion = recommendation_engine.generate_conclusion(insights_result)
    print(f"  Conclusion: {conclusion[:120]}...")
except Exception as e:
    print(f"  generate_conclusion FAILED: {e}")
    import traceback
    traceback.print_exc()

# ========== Module 8: Charts ==========
try:
    charts = chart_builder.generate_all_charts(df_clean, stats, anomalies, col_types)
    print(f"\n[Module 8] Charts: {len(charts)} generated")
    chart_bytes = {}
    for name, fig in charts.items():
        chart_bytes[name] = chart_builder.save_figure_to_bytes(fig)
        import matplotlib.pyplot as plt
        plt.close(fig)
    print(f"  Chart bytes: {list(chart_bytes.keys())}")
except Exception as e:
    print(f"[Module 8] FAILED: {e}")
    import traceback
    traceback.print_exc()
    chart_bytes = {}

# ========== Module 9: Report ==========
try:
    report_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    output_path = os.path.join(report_dir, 'test_report.pdf')
    result_path = report_builder.generate_pdf_report(
        output_path=output_path,
        dataset_info=dataset_info,
        session_id=1,
        statistics=stats,
        anomalies=anomalies,
        insights=insights_result,
        conclusion=conclusion if 'conclusion' in dir() else 'Test conclusion',
        recommendations=recs if 'recs' in dir() else [],
        charts=chart_bytes,
        include_charts=True,
    )
    file_size = os.path.getsize(result_path) if os.path.exists(result_path) else 0
    print(f"\n[Module 9] Report: generated -> {result_path} ({file_size} bytes)")
except Exception as e:
    print(f"\n[Module 9] FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n=== MODULES 6-9 TEST COMPLETE ===")
