"""
AEIA — Conclusion & Recommendation Engine (Module 7)

Generates the overall engineering conclusion and ranked recommendations
from session findings. Uses template-based NLG only (FR-055).

FRs implemented: FR-059 through FR-065.
Templates: implementation_specification.md §5.
Severity ranking: implementation_specification.md §4.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
from typing import Any, Dict, List, Optional

from core.insight_generator import TEMPLATES

logger = logging.getLogger('aeia.recommendation_engine')


# ---------------------------------------------------------------------------
# Severity ordering for ranking (FR-061)
# ---------------------------------------------------------------------------

SEVERITY_RANK = {
    'Critical': 0,
    'Warning': 1,
    'Info': 2,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_conclusion(insights: Dict[str, Any],
                        statistics: Optional[Dict[str, Any]] = None,
                        dataset_info: Optional[Dict[str, Any]] = None,
                        ) -> str:
    """Generate the overall Engineering Conclusion for the session.

    FR-059: Synthesize all findings into one overall conclusion.
    FR-064: If no anomalies or rule matches exist, generate a clear
            "No significant findings" conclusion.
    FR-055: Uses the executive_summary_composer for professional
            engineering prose with spaCy-assisted phrasing.

    Args:
        insights: Output of insight_generator.generate_insights().
        statistics: Output of statistics_engine.compute_statistics()
                    (optional, passed to composer for context).
        dataset_info: Dict with 'filename', 'row_count', etc.
                      (optional, passed to composer for context).

    Returns:
        The conclusion text string (executive summary prose).
    """
    from core.executive_summary_composer import compose_executive_summary

    result = compose_executive_summary(
        insights,
        statistics=statistics,
        dataset_info=dataset_info,
    )
    conclusion = result.get('text', '')

    if not conclusion:
        # Fallback to the no-findings template
        conclusion = TEMPLATES['no_findings_conclusion']
        logger.info('No findings — generated no-findings conclusion.')
    else:
        all_insights = insights.get('all_insights', [])
        highest_severity = _get_highest_severity(all_insights) if all_insights else 'Info'
        logger.info(
            'Generated executive summary conclusion: highest severity = %s, '
            '%d findings.', highest_severity, len(all_insights),
        )

    return conclusion


def generate_conclusion_with_metadata(
        insights: Dict[str, Any],
        statistics: Optional[Dict[str, Any]] = None,
        dataset_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate the conclusion with full traceability metadata.

    Like generate_conclusion(), but returns the full dict including
    paragraph-level source_findings for NFR-006 explainability.

    Returns:
        Dict with 'text' and 'paragraphs' (each with source_findings).
    """
    from core.executive_summary_composer import compose_executive_summary

    return compose_executive_summary(
        insights,
        statistics=statistics,
        dataset_info=dataset_info,
    )


def generate_recommendations(insights: Dict[str, Any],
                              rule_matches: List[Dict[str, Any]],
                              ) -> List[Dict[str, Any]]:
    """Generate ranked recommendations from findings and rule matches.

    FR-060: Tied to specific findings.
    FR-061: Ranked by severity (Critical → Warning → Info).
    FR-063: Reference the rule or detection method.
    FR-064: Empty list if no findings (caller uses the no-findings
            conclusion instead).

    Args:
        insights: Output of insight_generator.generate_insights().
        rule_matches: Output of expert_system.evaluate_rules().

    Returns:
        List of recommendation dicts, sorted Critical → Warning → Info.
        Each has:
        - 'text': The formatted recommendation text.
        - 'severity': 'Critical' / 'Warning' / 'Info'.
        - 'source_rule_id': The rule_id if from a rule, else None.
        - 'source_reference': Human-readable source (FR-063).
    """
    recommendations = []
    seen_sources = set()

    # Phase 1: Recommendations from rule matches that have recommendation_text
    for match in rule_matches:
        rec_text = match.get('recommendation_text')
        if not rec_text:
            continue

        rule_id = match.get('rule_id', '')
        severity = match.get('severity', 'Warning')

        # Avoid duplicate recommendations for the same rule
        if rule_id in seen_sources:
            continue
        seen_sources.add(rule_id)

        source_ref = f"Rule {rule_id}: {match.get('rule_name', '')}"
        formatted = TEMPLATES['recommendation'].format(
            severity=severity,
            recommendation_text=rec_text,
            source_reference=source_ref,
        )

        recommendations.append({
            'text': formatted,
            'severity': severity,
            'source_rule_id': rule_id,
            'source_reference': source_ref,
        })

    # Phase 2: Generic recommendations for anomalies without rule coverage
    all_insights = insights.get('all_insights', [])
    for insight in all_insights:
        finding_type = insight.get('finding_type', '')
        col = insight.get('column', '')
        severity = insight.get('severity', 'Warning')

        # Skip rule-sourced insights — they were handled in Phase 1
        if insight.get('source_type') == 'Rule':
            continue

        # Skip informational patterns (trends/correlations) unless
        # they have a severity above Info
        if severity == 'Info' and finding_type in ('Trend', 'Correlation'):
            continue

        source_key = f"{finding_type}:{col}"
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        # Generate a generic recommendation based on the detection method
        rec_text = _generic_recommendation(finding_type, col)
        if not rec_text:
            continue

        source_ref = f"{finding_type} detection on column '{col}'"
        formatted = TEMPLATES['recommendation'].format(
            severity=severity,
            recommendation_text=rec_text,
            source_reference=source_ref,
        )

        recommendations.append({
            'text': formatted,
            'severity': severity,
            'source_rule_id': None,
            'source_reference': source_ref,
        })

    # FR-061: Sort by severity (Critical → Warning → Info)
    recommendations.sort(key=lambda r: SEVERITY_RANK.get(r['severity'], 99))

    logger.info('Generated %d recommendations.', len(recommendations))
    return recommendations


def add_engineer_note(recommendation: Dict[str, Any],
                      note: str) -> Dict[str, Any]:
    """Add a free-text engineer annotation to a recommendation.

    FR-062: Allow the user to add notes/annotations to any finding or
    the overall conclusion before export.

    Args:
        recommendation: The recommendation dict to annotate.
        note: The engineer's free-text note.

    Returns:
        The updated recommendation dict.
    """
    recommendation['engineer_note'] = note
    return recommendation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_severities(insights: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count findings by severity level."""
    counts: Dict[str, int] = {}
    for insight in insights:
        sev = insight.get('severity', 'Warning')
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def _get_highest_severity(insights: List[Dict[str, Any]]) -> str:
    """Return the highest severity found among all insights.

    FR-061: Ranking order is Critical > Warning > Info.
    """
    severities = {i.get('severity', 'Warning') for i in insights}
    for level in ('Critical', 'Warning', 'Info'):
        if level in severities:
            return level
    return 'Info'


def _generic_recommendation(finding_type: str, column: str) -> Optional[str]:
    """Generate a generic recommendation for detection-only findings.

    These are used when the anomaly was not covered by a specific rule
    that has its own recommendation_text.
    """
    if finding_type == 'ZScore':
        return (
            f"Review the unusual value(s) in column '{column}' to determine "
            f"whether they represent a genuine anomaly or a measurement error."
        )
    elif finding_type == 'IQR':
        return (
            f"Investigate the out-of-range value(s) in column '{column}' "
            f"to assess whether they indicate a system issue."
        )
    elif finding_type == 'IsolationForest':
        return (
            f"Examine the flagged rows for unusual multivariate patterns. "
            f"These may indicate a system-level anomaly not visible in "
            f"individual columns."
        )
    return None
