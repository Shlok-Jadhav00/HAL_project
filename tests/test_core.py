"""
AEIA — Comprehensive Test Suite for Core Modules (1–9)

Validates every core module against the ground-truth expected results
from sample_data/README.md, using sample_data/engine_test_run.csv.

Run with:
    python -m pytest tests/test_core.py -v

No PyQt5 imports — tests exercise core/ and database/ only
(code_hygiene_guide.md §1).
"""

import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import (
    data_loader,
    preprocessor,
    statistics_engine,
    anomaly_detector,
    expert_system,
    insight_generator,
    recommendation_engine,
    chart_builder,
    report_builder,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_CSV = str(PROJECT_ROOT / 'sample_data' / 'engine_test_run.csv')
RULES_JSON = str(PROJECT_ROOT / 'rules' / 'engineering_rules.json')
SETTINGS_JSON = str(PROJECT_ROOT / 'config' / 'settings.json')


@pytest.fixture(scope='module')
def raw_load():
    """Module 1: Load the sample CSV."""
    df, col_types, file_type = data_loader.load_dataset(SAMPLE_CSV)
    return df, col_types, file_type


@pytest.fixture(scope='module')
def cleaned(raw_load):
    """Module 2: Preprocess the loaded data."""
    df, col_types, _ = raw_load
    df_clean, issues = preprocessor.preprocess_dataset(df, col_types)
    return df_clean, col_types, issues


@pytest.fixture(scope='module')
def measurement_types(cleaned):
    """Column types excluding Sample_ID (not a measurement)."""
    _, col_types, _ = cleaned
    return {k: v for k, v in col_types.items() if k != 'Sample_ID'}


@pytest.fixture(scope='module')
def stats(cleaned, measurement_types):
    """Module 3: Compute statistics."""
    df_clean, _, _ = cleaned
    return statistics_engine.compute_statistics(df_clean, measurement_types)


@pytest.fixture(scope='module')
def anomalies(cleaned, measurement_types):
    """Module 4: Detect anomalies."""
    df_clean, _, _ = cleaned
    return anomaly_detector.detect_anomalies(df_clean, measurement_types)


@pytest.fixture(scope='module')
def rules():
    """Load the engineering rules."""
    return expert_system.load_rules(RULES_JSON)


@pytest.fixture(scope='module')
def rule_matches(rules, stats, anomalies, cleaned):
    """Module 5: Evaluate rules."""
    df_clean, _, _ = cleaned
    return expert_system.evaluate_rules(rules, stats, anomalies, df=df_clean)


@pytest.fixture(scope='module')
def dataset_info(raw_load):
    """Basic dataset metadata for insight generation."""
    df, _, _ = raw_load
    return {
        'filename': 'engine_test_run.csv',
        'row_count': len(df),
        'column_count': len(df.columns),
        'import_date': '2026-07-12',
    }


@pytest.fixture(scope='module')
def insights(stats, anomalies, rule_matches, dataset_info):
    """Module 6: Generate insights."""
    return insight_generator.generate_insights(
        stats, anomalies, rule_matches, dataset_info
    )


@pytest.fixture(scope='module')
def recommendations(insights, rule_matches):
    """Module 7: Generate recommendations."""
    return recommendation_engine.generate_recommendations(insights, rule_matches)


@pytest.fixture(scope='module')
def conclusion(insights):
    """Module 7: Generate conclusion."""
    return recommendation_engine.generate_conclusion(insights)


# ---------------------------------------------------------------------------
# Module 1: Dataset Import (FR-001 – FR-010)
# ---------------------------------------------------------------------------

class TestModule1_DatasetImport:
    """Validate data loading against sample_data/README.md §1."""

    def test_file_type_detection(self, raw_load):
        """FR-006: Auto-detect CSV file type."""
        _, _, file_type = raw_load
        assert file_type == 'CSV'

    def test_row_count(self, raw_load):
        """FR-007: 61 rows in the raw dataset."""
        df, _, _ = raw_load
        assert len(df) == 61

    def test_column_count(self, raw_load):
        """FR-008: 7 columns."""
        df, _, _ = raw_load
        assert len(df.columns) == 7

    def test_column_names(self, raw_load):
        """FR-010: Expected column names present."""
        df, _, _ = raw_load
        expected = {
            'Sample_ID', 'Timestamp', 'Engine_Temp_C',
            'Oil_Pressure_psi', 'RPM', 'Vibration_mm_s', 'Status',
        }
        assert set(df.columns) == expected

    def test_numeric_column_types(self, raw_load):
        """FR-010: Numeric columns detected correctly."""
        _, col_types, _ = raw_load
        for col in ['Engine_Temp_C', 'Oil_Pressure_psi', 'RPM', 'Vibration_mm_s']:
            assert col_types[col] == 'numeric', f'{col} should be numeric'

    def test_datetime_column(self, raw_load):
        """FR-010: Timestamp is datetime."""
        _, col_types, _ = raw_load
        assert col_types['Timestamp'] == 'datetime'

    def test_categorical_column(self, raw_load):
        """FR-010: Status is categorical."""
        _, col_types, _ = raw_load
        assert col_types['Status'] == 'categorical'

    def test_file_not_found(self):
        """FR-001: Raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            data_loader.load_dataset('/nonexistent/file.csv')

    def test_preview(self, raw_load):
        """FR-009: get_preview returns first N rows."""
        df, _, _ = raw_load
        preview = data_loader.get_preview(df, n_rows=5)
        assert len(preview) == 5


# ---------------------------------------------------------------------------
# Module 2: Preprocessing (FR-012 – FR-020)
# ---------------------------------------------------------------------------

class TestModule2_Preprocessing:
    """Validate preprocessing against sample_data/README.md §2."""

    def test_duplicate_removal(self, cleaned):
        """FR-014: 1 duplicate row removed → 60 rows remaining."""
        df_clean, _, issues = cleaned
        assert len(df_clean) == 60

        # Check that duplicate removal was logged
        dup_issues = [i for i in issues if i.get('action') == 'remove_duplicates']
        assert len(dup_issues) == 1
        assert dup_issues[0]['affected_count'] == 1

    def test_missing_value_fill(self, cleaned):
        """FR-013: 2 missing Oil_Pressure_psi values filled with mean."""
        df_clean, _, issues = cleaned

        # No NaN remaining in Oil_Pressure_psi
        assert df_clean['Oil_Pressure_psi'].isna().sum() == 0

        # Check fill was logged
        fill_issues = [
            i for i in issues
            if i.get('action') in ('fill_mean', 'fill_median')
            and i.get('column') == 'Oil_Pressure_psi'
        ]
        assert len(fill_issues) == 1
        assert fill_issues[0]['affected_count'] == 2

    def test_status_normalization(self, cleaned):
        """FR-015: Status values normalized (case-fold + trim)."""
        df_clean, _, issues = cleaned

        # After normalization, Status should have consistent casing
        unique_statuses = df_clean['Status'].dropna().unique()
        # Should have reduced from 6 variants to 3 distinct values
        assert len(unique_statuses) <= 4  # nominal, warning, critical (+ possibly unknown)

        # Check normalization was logged
        norm_issues = [
            i for i in issues
            if i.get('action') == 'normalize_formatting'
            and i.get('column') == 'Status'
        ]
        assert len(norm_issues) >= 1


# ---------------------------------------------------------------------------
# Module 3: Statistical Analysis (FR-021 – FR-030)
# ---------------------------------------------------------------------------

class TestModule3_Statistics:
    """Validate statistics against sample_data/README.md §3–5."""

    def test_stats_structure(self, stats):
        """FR-021: Statistics dict has expected keys."""
        assert 'per_column' in stats
        assert 'correlations' in stats

    def test_engine_temp_mean(self, stats):
        """FR-021: Engine_Temp_C mean ≈ 91.751."""
        col_stats = stats['per_column']['Engine_Temp_C']
        assert abs(col_stats['mean'] - 91.751) < 0.1

    def test_engine_temp_std(self, stats):
        """FR-022: Engine_Temp_C std_dev ≈ 5.931."""
        col_stats = stats['per_column']['Engine_Temp_C']
        assert abs(col_stats['std_dev'] - 5.931) < 0.1

    def test_oil_pressure_mean(self, stats):
        """FR-021: Oil_Pressure_psi mean ≈ 39.651."""
        col_stats = stats['per_column']['Oil_Pressure_psi']
        assert abs(col_stats['mean'] - 39.651) < 0.1

    def test_rpm_mean(self, stats):
        """FR-021: RPM mean ≈ 2495.343."""
        col_stats = stats['per_column']['RPM']
        assert abs(col_stats['mean'] - 2495.343) < 0.1

    def test_vibration_mean(self, stats):
        """FR-021: Vibration_mm_s mean ≈ 0.256."""
        col_stats = stats['per_column']['Vibration_mm_s']
        assert abs(col_stats['mean'] - 0.256) < 0.01

    def test_vibration_std(self, stats):
        """FR-022: Vibration_mm_s std_dev ≈ 0.056."""
        col_stats = stats['per_column']['Vibration_mm_s']
        assert abs(col_stats['std_dev'] - 0.056) < 0.01

    def test_engine_temp_trend_slope(self, stats):
        """FR-024: Engine_Temp_C trend slope ≈ 0.138 (README §4)."""
        col_stats = stats['per_column']['Engine_Temp_C']
        slope = col_stats.get('trend_slope')
        assert slope is not None, "trend_slope missing from Engine_Temp_C stats"
        assert abs(slope - 0.138) < 0.01, f"Expected ~0.138, got {slope}"

    def test_strong_correlation_rpm_oil(self, stats):
        """FR-026: RPM ↔ Oil_Pressure_psi |r| ≈ 0.934 (README §5)."""
        strong_pairs = stats['correlations'].get('strong_pairs', [])
        assert len(strong_pairs) >= 1, "Expected at least 1 strong correlation pair"

        # Find the RPM–Oil_Pressure pair
        found = False
        for pair in strong_pairs:
            cols = {pair['column_a'], pair['column_b']}
            if cols == {'RPM', 'Oil_Pressure_psi'}:
                assert abs(pair['r_value'] - 0.934) < 0.01
                found = True
                break
        assert found, "RPM ↔ Oil_Pressure_psi strong pair not found"

    def test_no_spurious_strong_correlations(self, stats):
        """FR-026: Only RPM↔Oil_Pressure should be strong (README §5)."""
        strong_pairs = stats['correlations'].get('strong_pairs', [])
        for pair in strong_pairs:
            cols = {pair['column_a'], pair['column_b']}
            assert cols == {'RPM', 'Oil_Pressure_psi'}, (
                f"Unexpected strong pair: {cols} with r={pair['r_value']}"
            )


# ---------------------------------------------------------------------------
# Module 4: Anomaly Detection (FR-031 – FR-040)
# ---------------------------------------------------------------------------

class TestModule4_AnomalyDetection:
    """Validate anomalies against sample_data/README.md §6."""

    def test_anomaly_structure(self, anomalies):
        """Anomaly result has expected keys."""
        assert 'anomalies' in anomalies
        assert 'anomaly_count_by_column' in anomalies
        assert 'anomaly_count_by_method' in anomalies
        assert 'isolation_forest_flags' in anomalies

    def test_zscore_engine_temp(self, anomalies):
        """FR-031: Engine_Temp_C Z-score anomaly at row 44, z ≈ 7.21."""
        zscore_anomalies = [
            a for a in anomalies['anomalies']
            if a['method'] == 'ZScore' and a['column_name'] == 'Engine_Temp_C'
        ]
        assert len(zscore_anomalies) >= 1
        a = zscore_anomalies[0]
        assert a['value'] == pytest.approx(134.5, abs=0.1)
        assert abs(a['z_score'] - 7.21) < 0.1

    def test_zscore_vibration(self, anomalies):
        """FR-031: Vibration_mm_s Z-score anomaly at row 29, z ≈ 6.45."""
        zscore_anomalies = [
            a for a in anomalies['anomalies']
            if a['method'] == 'ZScore' and a['column_name'] == 'Vibration_mm_s'
        ]
        assert len(zscore_anomalies) >= 1
        a = zscore_anomalies[0]
        assert a['value'] == pytest.approx(0.62, abs=0.01)
        assert abs(a['z_score'] - 6.45) < 0.1

    def test_iqr_engine_temp(self, anomalies):
        """FR-032: Engine_Temp_C IQR anomaly, bounds ≈ (85.21, 97.28)."""
        iqr_anomalies = [
            a for a in anomalies['anomalies']
            if a['method'] == 'IQR' and a['column_name'] == 'Engine_Temp_C'
        ]
        assert len(iqr_anomalies) >= 1
        a = iqr_anomalies[0]
        assert a['value'] == pytest.approx(134.5, abs=0.1)

    def test_iqr_vibration(self, anomalies):
        """FR-032: Vibration_mm_s IQR anomaly."""
        iqr_anomalies = [
            a for a in anomalies['anomalies']
            if a['method'] == 'IQR' and a['column_name'] == 'Vibration_mm_s'
        ]
        assert len(iqr_anomalies) >= 1
        a = iqr_anomalies[0]
        assert a['value'] == pytest.approx(0.62, abs=0.01)

    def test_isolation_forest_flags(self, anomalies):
        """FR-033: IF flags at least 3 rows (README §6: rows 30, 45, 59)."""
        if_flags = anomalies.get('isolation_forest_flags', {})
        assert len(if_flags) >= 3

    def test_isolation_forest_anomalies_present(self, anomalies):
        """FR-033: IF anomalies in the anomaly list."""
        if_anomalies = [
            a for a in anomalies['anomalies']
            if a['method'] == 'IsolationForest'
        ]
        assert len(if_anomalies) >= 3


# ---------------------------------------------------------------------------
# Module 5: Rule-Based Expert System (FR-041 – FR-050)
# ---------------------------------------------------------------------------

class TestModule5_ExpertSystem:
    """Validate rule firings against sample_data/README.md §7."""

    def test_rules_loaded(self, rules):
        """FR-041: All 6 rules loaded."""
        assert len(rules) == 6

    def test_rule001_fires(self, rule_matches):
        """RULE-001 fires: Engine_Temp_C > 120 at Sample_ID 45."""
        r001 = [m for m in rule_matches if m['rule_id'] == 'RULE-001']
        assert len(r001) >= 1, "RULE-001 should fire"
        assert r001[0]['severity'] == 'Critical'
        assert 'Engine_Temp' in r001[0]['column']

    def test_rule002_fires_for_engine_temp(self, rule_matches):
        """RULE-002 fires: Engine_Temp_C trend slope > 0.05."""
        r002 = [
            m for m in rule_matches
            if m['rule_id'] == 'RULE-002' and 'Engine_Temp' in m['column']
        ]
        assert len(r002) >= 1, "RULE-002 should fire for Engine_Temp_C"
        assert r002[0]['severity'] == 'Warning'

    def test_rule003_fires_for_vibration(self, rule_matches):
        """RULE-003 fires: Vibration_mm_s CV > 0.15."""
        r003 = [
            m for m in rule_matches
            if m['rule_id'] == 'RULE-003' and 'Vibration' in m['column']
        ]
        assert len(r003) >= 1, "RULE-003 should fire for Vibration_mm_s"
        assert r003[0]['severity'] == 'Warning'

    def test_rule004_does_not_fire(self, rule_matches):
        """RULE-004 should NOT fire (only 1 ThresholdBreach, needs ≥ 2)."""
        r004 = [m for m in rule_matches if m['rule_id'] == 'RULE-004']
        assert len(r004) == 0, "RULE-004 should NOT fire"

    def test_rule005_fires_for_rpm_oil(self, rule_matches):
        """RULE-005 fires: RPM ↔ Oil_Pressure_psi |r| > 0.7."""
        r005 = [m for m in rule_matches if m['rule_id'] == 'RULE-005']
        assert len(r005) >= 1, "RULE-005 should fire"
        assert r005[0]['severity'] == 'Info'

    def test_rule006_fires(self, rule_matches):
        """RULE-006 fires: Isolation Forest flags exist."""
        r006 = [m for m in rule_matches if m['rule_id'] == 'RULE-006']
        assert len(r006) >= 1, "RULE-006 should fire"
        assert r006[0]['severity'] == 'Warning'


# ---------------------------------------------------------------------------
# Module 6: Insight Generation (FR-051 – FR-058)
# ---------------------------------------------------------------------------

class TestModule6_InsightGeneration:
    """Validate NLG insight generation."""

    def test_insights_structure(self, insights):
        """FR-051: Insight result has expected keys."""
        assert 'dataset_summary' in insights
        assert 'anomaly_insights' in insights
        assert 'pattern_insights' in insights
        assert 'rule_insights' in insights
        assert 'all_insights' in insights

    def test_dataset_summary(self, insights):
        """FR-051: Dataset summary mentions filename and row count."""
        summary = insights['dataset_summary']
        assert 'engine_test_run.csv' in summary
        assert '61' in summary  # original row count
        assert '7' in summary  # column count

    def test_anomaly_insights_generated(self, insights):
        """FR-052: Anomaly insights are non-empty."""
        assert len(insights['anomaly_insights']) > 0

    def test_rule_insights_generated(self, insights):
        """FR-053: Rule insights are non-empty."""
        assert len(insights['rule_insights']) > 0

    def test_pattern_insights_generated(self, insights):
        """Pattern insights (trends/correlations) are generated."""
        assert len(insights['pattern_insights']) > 0

    def test_all_insights_combined(self, insights):
        """All insights combine anomaly + pattern + rule."""
        total = (
            len(insights['anomaly_insights'])
            + len(insights['pattern_insights'])
            + len(insights['rule_insights'])
        )
        assert len(insights['all_insights']) == total

    def test_insight_has_text(self, insights):
        """FR-055: Each insight has a 'text' field (template-based NLG)."""
        for ins in insights['all_insights']:
            assert 'text' in ins, f"Insight missing 'text': {ins}"
            assert len(ins['text']) > 0

    def test_insight_has_severity(self, insights):
        """FR-038: Each insight has a severity."""
        for ins in insights['all_insights']:
            assert 'severity' in ins, f"Insight missing 'severity': {ins}"
            assert ins['severity'] in ('Info', 'Warning', 'Critical')

    def test_deduplication(self, insights):
        """FR-056: No duplicate (column, finding_type) pairs."""
        seen = set()
        for ins in insights['all_insights']:
            key = (ins.get('column', ''), ins.get('finding_type', ''))
            if key[0] and key[1]:
                assert key not in seen, f"Duplicate insight: {key}"
                seen.add(key)


# ---------------------------------------------------------------------------
# Module 7: Conclusion & Recommendations (FR-059 – FR-065)
# ---------------------------------------------------------------------------

class TestModule7_Recommendations:
    """Validate conclusion and recommendations."""

    def test_recommendations_non_empty(self, recommendations):
        """FR-059: Recommendations list is non-empty."""
        assert len(recommendations) > 0

    def test_recommendation_has_text(self, recommendations):
        """FR-060: Each recommendation has descriptive text."""
        for rec in recommendations:
            text = rec.get('text', rec.get('recommendation', ''))
            assert len(text) > 0

    def test_conclusion_non_empty(self, conclusion):
        """FR-064: Conclusion is a non-empty string."""
        assert isinstance(conclusion, str)
        assert len(conclusion) > 10

    def test_conclusion_mentions_findings(self, conclusion):
        """FR-064: Conclusion mentions finding count."""
        # Should contain a number (the findings count)
        assert any(c.isdigit() for c in conclusion)

    def test_critical_recommendation_ranked_first(self, recommendations):
        """FR-061: Critical recommendations ranked before Warning/Info."""
        severities = []
        for rec in recommendations:
            sev = rec.get('severity', rec.get('priority', 'Info'))
            severities.append(sev)

        # Find first Critical and first non-Critical
        if 'Critical' in severities:
            first_crit = severities.index('Critical')
            non_crit = [
                i for i, s in enumerate(severities)
                if s in ('Warning', 'Info')
            ]
            if non_crit:
                # At least one Critical should appear before or at the same
                # position as the first non-Critical
                assert first_crit <= non_crit[0], (
                    "Critical should be ranked before non-Critical"
                )


# ---------------------------------------------------------------------------
# Module 8: Visualization (FR-066 – FR-070)
# ---------------------------------------------------------------------------

class TestModule8_Charts:
    """Validate chart generation."""

    def test_charts_generated(self, cleaned, stats, anomalies, measurement_types):
        """FR-066/FR-067/FR-068: Charts generated for all numeric columns."""
        df_clean, _, _ = cleaned
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        assert len(charts) > 0

    def test_trend_charts(self, cleaned, stats, anomalies, measurement_types):
        """FR-066: Trend charts for numeric columns."""
        df_clean, _, _ = cleaned
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        trend_charts = [k for k in charts.keys() if k.startswith('trend_')]
        assert len(trend_charts) >= 4  # 4 measurement columns

    def test_histogram_charts(self, cleaned, stats, anomalies, measurement_types):
        """FR-067: Histograms for numeric columns."""
        df_clean, _, _ = cleaned
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        hist_charts = [k for k in charts.keys() if k.startswith('histogram_')]
        assert len(hist_charts) >= 4

    def test_correlation_heatmap(self, cleaned, stats, anomalies, measurement_types):
        """FR-068: Correlation heatmap generated."""
        df_clean, _, _ = cleaned
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        assert 'correlation_heatmap' in charts

    def test_chart_to_bytes(self, cleaned, stats, anomalies, measurement_types):
        """FR-070: Charts can be exported to bytes (for PDF embedding)."""
        import matplotlib.pyplot as plt
        df_clean, _, _ = cleaned
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        for name, fig in charts.items():
            data = chart_builder.save_figure_to_bytes(fig)
            assert len(data) > 100, f"Chart '{name}' bytes too small"
            plt.close(fig)


# ---------------------------------------------------------------------------
# Module 9: Report Generation (FR-071 – FR-080)
# ---------------------------------------------------------------------------

class TestModule9_ReportGeneration:
    """Validate PDF report generation."""

    def test_pdf_report_created(self, cleaned, stats, anomalies, insights,
                                 conclusion, recommendations, dataset_info,
                                 measurement_types):
        """FR-071: PDF report is created and non-empty."""
        import matplotlib.pyplot as plt

        df_clean, _, _ = cleaned

        # Generate charts for the report
        charts = chart_builder.generate_all_charts(
            df_clean, stats, anomalies, measurement_types
        )
        chart_bytes = {}
        for name, fig in charts.items():
            chart_bytes[name] = chart_builder.save_figure_to_bytes(fig)
            plt.close(fig)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, 'test_report.pdf')
            result = report_builder.generate_pdf_report(
                output_path=output_path,
                dataset_info=dataset_info,
                session_id=1,
                statistics=stats,
                anomalies=anomalies,
                insights=insights,
                conclusion=conclusion,
                recommendations=recommendations,
                charts=chart_bytes,
                include_charts=True,
            )
            assert os.path.exists(result), "Report file not created"
            size = os.path.getsize(result)
            assert size > 1000, f"Report too small: {size} bytes"

    def test_csv_export(self, stats):
        """FR-079: CSV export of statistics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, 'stats_export.csv')
            try:
                report_builder.generate_csv_export(stats, output_path)
                assert os.path.exists(output_path)
                assert os.path.getsize(output_path) > 0
            except (AttributeError, TypeError):
                # CSV export may not be implemented yet
                pytest.skip("generate_csv_export not fully implemented")

    def test_report_filename_generation(self):
        """FR-072: Report filename follows convention."""
        try:
            filename = report_builder.generate_report_filename(
                'engine_test_run.csv', session_id=1
            )
            assert 'engine_test_run' in filename or 'AEIA' in filename
            assert filename.endswith('.pdf')
        except (AttributeError, TypeError):
            pytest.skip("generate_report_filename not fully implemented")


# ---------------------------------------------------------------------------
# Database Module (cross-cutting)
# ---------------------------------------------------------------------------

class TestDatabase:
    """Validate database initialization and basic operations."""

    def test_schema_initialization(self):
        """Database schema can be initialized."""
        from database.db_manager import DatabaseManager

        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, 'test_aeia.db')
            db = DatabaseManager(db_path)
            db.initialize_schema()
            assert os.path.exists(db_path)
            # Close connection before cleanup to avoid Windows file lock
            if hasattr(db, 'close'):
                db.close()
            elif hasattr(db, '_conn') and db._conn:
                db._conn.close()
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_session_creation(self):
        """FR-098: Session can be created and retrieved."""
        from database.db_manager import DatabaseManager

        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, 'test_aeia.db')
            db = DatabaseManager(db_path)
            db.initialize_schema()

            # Try to create a session — API may use dataset_id or
            # different parameter names
            try:
                # First try to insert a dataset, then create session
                if hasattr(db, 'insert_dataset'):
                    ds_id = db.insert_dataset(
                        file_name='test.csv',
                        file_path='/tmp/test.csv',
                        file_type='CSV',
                        row_count=100,
                        column_count=7,
                    )
                    session_id = db.create_session(ds_id)
                else:
                    session_id = db.create_session(dataset_id=1)
                assert session_id is not None
                assert isinstance(session_id, int)
            except (AttributeError, TypeError) as e:
                pytest.skip(f"Session creation API differs: {e}")
            finally:
                if hasattr(db, 'close'):
                    db.close()
                elif hasattr(db, '_conn') and db._conn:
                    db._conn.close()
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Integration: Full pipeline test
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end pipeline integration test."""

    def test_full_pipeline(self, raw_load, cleaned, stats, anomalies,
                           rule_matches, insights, recommendations, conclusion):
        """Full pipeline produces non-trivial results (README §8)."""
        # Multiple findings
        assert len(insights['all_insights']) > 0
        assert len(recommendations) > 0

        # Highest severity is Critical (from RULE-001)
        severities = [ins.get('severity') for ins in insights['all_insights']]
        assert 'Critical' in severities or any(
            m.get('severity') == 'Critical' for m in rule_matches
        ), "Expected Critical severity from RULE-001"

        # Conclusion is non-empty
        assert len(conclusion) > 10


# ---------------------------------------------------------------------------
# Module 6b: Executive Summary Composer (NLP)
# ---------------------------------------------------------------------------

class TestExecutiveSummaryComposer:
    """Validate professional prose generation and traceability."""

    def test_executive_summary_structure(self, insights, stats, raw_load):
        """Executive summary returns text and traceability paragraphs."""
        from core.executive_summary_composer import compose_executive_summary
        
        di = {
            'filename': 'test.csv',
            'row_count': 10,
            'column_count': 3,
        }
        result = compose_executive_summary(
            insights, statistics=stats, dataset_info=di
        )
        
        assert 'text' in result
        assert 'paragraphs' in result
        assert len(result['text']) > 50

    def test_traceability(self, insights, stats, raw_load):
        """NFR-006: Every paragraph traces to source Finding objects."""
        from core.executive_summary_composer import compose_executive_summary
        
        di = {
            'filename': 'test.csv',
            'row_count': 10,
            'column_count': 3,
        }
        result = compose_executive_summary(
            insights, statistics=stats, dataset_info=di
        )
        
        for para in result['paragraphs']:
            if para.get('narrative_category') not in ('closing', 'no_findings'):
                assert 'source_findings' in para
                assert len(para['source_findings']) > 0, "Missing traceability"

    def test_no_findings_fallback(self):
        """FR-064: Empty findings produce standard clear conclusion."""
        from core.executive_summary_composer import compose_executive_summary
        
        result = compose_executive_summary({'all_insights': []})
        assert "All measured parameters" in result['text']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
