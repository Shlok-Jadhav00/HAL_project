"""
AEIA — Insight & Natural Language Summary Generation (Module 6)

Generates plain-language descriptions of findings using template-based
NLG. No generative LLM — templates only (FR-055).

FRs implemented: FR-051 through FR-058.
Templates: implementation_specification.md §5.
Deduplication: FR-056.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger('aeia.insight_generator')


# ---------------------------------------------------------------------------
# NLG Templates (implementation_specification.md §5 — exact wording)
# ---------------------------------------------------------------------------

TEMPLATES = {
    "dataset_summary":
        "The dataset '{filename}' contains {row_count} rows across {column_count} columns, "
        "imported on {import_date}.",

    "zscore_anomaly":
        "Column '{column}' shows an unusual value of {value} at row {row}, which is {z_score} "
        "standard deviations from the mean — flagged as a statistical outlier ({severity}).",

    "iqr_anomaly":
        "Column '{column}' has a value of {value} at row {row} that falls outside the expected "
        "range (below {lower_bound} or above {upper_bound}) — flagged as an outlier ({severity}).",

    "isolation_forest_anomaly":
        "Row {row} was flagged as an unusual combination of values across {columns_involved} — "
        "this pattern does not resemble the rest of the dataset ({severity}).",

    "trend_pattern":
        "Column '{column}' shows a {direction} trend over the dataset (slope = {slope}).",

    "correlation_pattern":
        "Columns '{column_a}' and '{column_b}' are strongly correlated (r = {r_value}), "
        "suggesting a possible relationship worth investigating.",

    "rule_fired":
        "{conclusion_text} (triggered because {matched_on}).",

    "recommendation":
        "{severity}: {recommendation_text} (Source: {source_reference}).",

    "no_findings_conclusion":
        "No significant anomalies, threshold breaches, or rule matches were found in this dataset. "
        "The data appears to be within expected engineering parameters.",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_insights(statistics: Dict[str, Any],
                      anomalies: Dict[str, Any],
                      rule_matches: List[Dict[str, Any]],
                      dataset_info: Dict[str, Any],
                      excluded_anomalies: Optional[Set[Tuple[str, int]]] = None,
                      ) -> Dict[str, Any]:
    """Generate all plain-language insights for a session.

    FR-051: Dataset summary.
    FR-052: Anomaly descriptions.
    FR-053: Rule match descriptions.
    FR-054: Group findings by column/subsystem.
    FR-056: Deduplicate by (column, finding_type).
    FR-057: Respect excluded false positives (FR-039).
    FR-058: No internet connection required.

    Args:
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        rule_matches: Output of expert_system.evaluate_rules().
        dataset_info: Dict with 'filename', 'row_count', 'column_count',
                      'import_date' keys.
        excluded_anomalies: Set of (column_name, row_reference) tuples
                           for false positives to skip (FR-039).

    Returns:
        Dict with keys:
        - 'dataset_summary': str
        - 'anomaly_insights': List[Dict] — each with 'text', 'column',
          'finding_type', 'severity'
        - 'pattern_insights': List[Dict] — trend and correlation insights
        - 'rule_insights': List[Dict] — rule-fired insights
        - 'all_insights': List[Dict] — combined, deduplicated, ordered
        - 'grouped_by_column': Dict[column → List[Dict]] (FR-054)
    """
    if excluded_anomalies is None:
        excluded_anomalies = set()

    # Track seen (column, finding_type) pairs for deduplication (FR-056)
    seen: Set[Tuple[str, str]] = set()

    # FR-051: Dataset summary
    dataset_summary = _generate_dataset_summary(dataset_info)

    # FR-052: Anomaly insights
    anomaly_insights = _generate_anomaly_insights(
        anomalies, excluded_anomalies, seen
    )

    # Pattern insights (trends and correlations)
    pattern_insights = _generate_pattern_insights(statistics, seen)

    # FR-053: Rule match insights
    rule_insights = _generate_rule_insights(rule_matches, seen)

    # Combine all insights
    all_insights = anomaly_insights + pattern_insights + rule_insights
    all_insights = _apply_confidence_matrix(all_insights)

    # FR-054: Group by column/subsystem
    grouped = _group_by_column(all_insights)

    logger.info(
        'Generated %d insights (%d anomaly, %d pattern, %d rule).',
        len(all_insights), len(anomaly_insights),
        len(pattern_insights), len(rule_insights),
    )

    return {
        'dataset_summary': dataset_summary,
        'anomaly_insights': anomaly_insights,
        'pattern_insights': pattern_insights,
        'rule_insights': rule_insights,
        'all_insights': all_insights,
        'grouped_by_column': grouped,
    }



def _apply_confidence_matrix(all_insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply the confidence-based severity prioritization (Confidence Matrix).

    FR-038: Prioritize findings dynamically based on overlapping evidence.
    """
    from collections import defaultdict
    import re

    # 1. Group by row/col
    row_findings = defaultdict(list)
    dataset_findings = []

    for insight in all_insights:
        row = insight.get('row_reference')
        col = insight.get('column', '')
        if row is None or row == 0 or row == '' or insight.get('finding_type') in ('Trend', 'Correlation'):
            dataset_findings.append(insight)
        else:
            row_findings[(col, str(row))].append(insight)

    # 2. Evaluate confidence for each group
    filtered_insights = list(dataset_findings)
    for (col, row), group in row_findings.items():
        stat_detectors = [f for f in group if f.get('source_type') in ('Statistic', 'Anomaly')]
        rule_detectors = [f for f in group if f.get('source_type') == 'Rule']

        has_stats = len(stat_detectors) > 0
        multiple_stats = len(stat_detectors) > 1
        has_rules = len(rule_detectors) > 0

        # Check for hardcoded critical rules (Option B)
        has_hard_critical = any(r.get('severity') == 'Critical' for r in rule_detectors)

        new_severity = 'Info'
        if has_hard_critical:
            new_severity = 'Critical'
        elif has_rules and has_stats:
            new_severity = 'Critical'
        elif multiple_stats:
            new_severity = 'Warning'
        elif has_rules and not has_stats:
            new_severity = 'Warning'
        else:
            new_severity = 'Info'

        # If a rule matches and stats also flag it, keep only the rule (FR-056)
        if has_rules and has_stats:
            kept_insights = rule_detectors
        else:
            kept_insights = group

        for insight in kept_insights:
            if insight.get('severity') == 'Critical' and insight.get('source_type') == 'Rule':
                insight['severity'] = 'Critical'
            else:
                insight['severity'] = new_severity

            # Update the text to reflect the new severity if it's in the text
            text = insight.get('text', '')
            insight['text'] = re.sub(r'\((Info|Warning|Critical)\)', f'({insight["severity"]})', text)
            
            filtered_insights.append(insight)

    return filtered_insights


def regenerate_insights(statistics: Dict[str, Any],
                        anomalies: Dict[str, Any],
                        rule_matches: List[Dict[str, Any]],
                        dataset_info: Dict[str, Any],
                        excluded_anomalies: Optional[Set[Tuple[str, int]]] = None,
                        ) -> Dict[str, Any]:
    """Regenerate insights after false-positive exclusions.

    FR-057: Allow user to regenerate after marking false positives.

    This is a thin wrapper around generate_insights() — the exclusion
    set is what changes between calls.
    """
    return generate_insights(
        statistics, anomalies, rule_matches, dataset_info,
        excluded_anomalies=excluded_anomalies,
    )


# ---------------------------------------------------------------------------
# Dataset summary (FR-051)
# ---------------------------------------------------------------------------

def _generate_dataset_summary(dataset_info: Dict[str, Any]) -> str:
    """Generate the dataset overview sentence.

    FR-051: Plain-language summary of row/column counts, key statistics.
    Template: implementation_specification.md §5 'dataset_summary'.
    """
    return TEMPLATES['dataset_summary'].format(
        filename=dataset_info.get('filename', 'unknown'),
        row_count=dataset_info.get('row_count', 0),
        column_count=dataset_info.get('column_count', 0),
        import_date=dataset_info.get('import_date', 'unknown'),
    )


# ---------------------------------------------------------------------------
# Anomaly insights (FR-052)
# ---------------------------------------------------------------------------

def _generate_anomaly_insights(anomalies: Dict[str, Any],
                                excluded: Set[Tuple[str, int]],
                                seen: Set[Tuple[str, str]],
                                ) -> List[Dict[str, Any]]:
    """Generate insights for detected anomalies.

    FR-052: Plain-language description for each anomaly.
    FR-056: Deduplicate by (column, finding_type).
    FR-057: Skip excluded false positives.
    """
    insights = []
    anomaly_list = anomalies.get('anomalies', [])

    for anomaly in anomaly_list:
        col = anomaly.get('column_name', '')
        row = anomaly.get('row_reference', 0)
        method = anomaly.get('method', '')

        # FR-039/FR-057: Skip false positives
        if (col, row) in excluded:
            continue

        # FR-056: Deduplication by (column, finding_type)
        dedup_key = (col, method)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        text = _format_anomaly(anomaly)
        if text:
            insights.append({
                'text': text,
                'column': col,
                'finding_type': method,
                'severity': anomaly.get('severity', 'Warning'),
                'source_type': 'Anomaly',
                'row_reference': row,
            })

    return insights


def _format_anomaly(anomaly: Dict[str, Any]) -> Optional[str]:
    """Format a single anomaly into NLG text using the appropriate template."""
    method = anomaly.get('method', '')
    severity = anomaly.get('severity', 'Warning')

    if method == 'ZScore':
        return TEMPLATES['zscore_anomaly'].format(
            column=anomaly.get('column_name', ''),
            value=anomaly.get('value', ''),
            row=anomaly.get('row_reference', ''),
            z_score=anomaly.get('z_score', ''),
            severity=severity,
        )
    elif method == 'IQR':
        return TEMPLATES['iqr_anomaly'].format(
            column=anomaly.get('column_name', ''),
            value=anomaly.get('value', ''),
            row=anomaly.get('row_reference', ''),
            lower_bound=anomaly.get('lower_bound', ''),
            upper_bound=anomaly.get('upper_bound', ''),
            severity=severity,
        )
    elif method == 'IsolationForest':
        columns = anomaly.get('columns_involved', [])
        columns_str = ', '.join(columns) if isinstance(columns, list) else str(columns)
        return TEMPLATES['isolation_forest_anomaly'].format(
            row=anomaly.get('row_reference', ''),
            columns_involved=columns_str,
            severity=severity,
        )
    else:
        logger.warning('Unknown anomaly method: %s', method)
        return None


# ---------------------------------------------------------------------------
# Pattern insights (trends and correlations)
# ---------------------------------------------------------------------------

def _generate_pattern_insights(statistics: Dict[str, Any],
                                seen: Set[Tuple[str, str]],
                                ) -> List[Dict[str, Any]]:
    """Generate insights for detected trends and correlations.

    FR-024 / FR-036: Trend patterns.
    FR-025 / FR-026: Correlation patterns.
    """
    insights = []

    # Trend insights
    per_column = statistics.get('per_column', {})
    for col, col_stats in per_column.items():
        direction = col_stats.get('trend_direction')
        slope = col_stats.get('trend_slope')

        # Only generate insight for non-Stable trends
        if direction and direction != 'Stable' and slope is not None:
            dedup_key = (col, 'Trend')
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            text = TEMPLATES['trend_pattern'].format(
                column=col,
                direction=direction,
                slope=f'{slope:.4f}',
            )
            insights.append({
                'text': text,
                'column': col,
                'finding_type': 'Trend',
                'severity': 'Info',
                'source_type': 'Statistic',
            })

    # Correlation insights
    strong_pairs = statistics.get('correlations', {}).get('strong_pairs', [])
    for pair in strong_pairs:
        col_a = pair.get('column_a', '')
        col_b = pair.get('column_b', '')
        r_value = pair.get('r_value', 0)

        # Use sorted pair name for deduplication
        pair_key = ','.join(sorted([col_a, col_b]))
        dedup_key = (pair_key, 'Correlation')
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        text = TEMPLATES['correlation_pattern'].format(
            column_a=col_a,
            column_b=col_b,
            r_value=f'{r_value:.4f}',
        )
        insights.append({
            'text': text,
            'column': pair_key,
            'finding_type': 'Correlation',
            'severity': 'Info',
            'source_type': 'Statistic',
        })

    return insights


# ---------------------------------------------------------------------------
# Rule match insights (FR-053)
# ---------------------------------------------------------------------------

def _generate_rule_insights(rule_matches: List[Dict[str, Any]],
                             seen: Set[Tuple[str, str]],
                             ) -> List[Dict[str, Any]]:
    """Generate insights for fired expert-system rules.

    FR-053: Plain-language description for each fired rule.
    FR-056: Deduplicate by (column, finding_type).
    """
    insights = []

    for match in rule_matches:
        col = match.get('column', '*')
        rule_id = match.get('rule_id', '')

        # FR-056: Deduplication
        dedup_key = (col, f'Rule:{rule_id}')
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        text = TEMPLATES['rule_fired'].format(
            conclusion_text=match.get('conclusion_text', ''),
            matched_on=match.get('matched_on', ''),
        )
        insights.append({
            'text': text,
            'column': col,
            'finding_type': f'Rule:{rule_id}',
            'severity': match.get('severity', 'Warning'),
            'source_type': 'Rule',
            'rule_id': rule_id,
            'rule_name': match.get('rule_name', ''),
            'recommendation_text': match.get('recommendation_text'),
        })

    return insights


# ---------------------------------------------------------------------------
# Grouping by column/subsystem (FR-054)
# ---------------------------------------------------------------------------

def _group_by_column(insights: List[Dict[str, Any]],
                      ) -> Dict[str, List[Dict[str, Any]]]:
    """Group findings into a structured section by column/subsystem.

    FR-054: Group individual findings by column name for the
    'Engineering Findings' section of the report.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for insight in insights:
        col = insight.get('column', 'General')
        if col not in grouped:
            grouped[col] = []
        grouped[col].append(insight)

    return grouped
