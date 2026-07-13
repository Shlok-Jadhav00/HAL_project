"""
AEIA — Rule-Based Expert System (Module 5)

Loads, validates, and evaluates engineering rules from
rules/engineering_rules.json against session analysis results.

FRs implemented: FR-041 through FR-050.
Rule schema: implementation_specification.md §3.
Validation target: sample_data/README.md §7.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import fnmatch
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger('aeia.expert_system')


# ---------------------------------------------------------------------------
# Valid metric and operator values (implementation_specification.md §3)
# ---------------------------------------------------------------------------

VALID_METRICS = {
    'raw_value', 'mean', 'std_dev', 'trend_slope',
    'coefficient_of_variation', 'correlation', 'anomaly_count',
    'isolation_forest_flag',
}

VALID_OPERATORS = {'>', '>=', '<', '<=', '==', '!='}

REQUIRED_RULE_FIELDS = {'rule_id', 'rule_name', 'is_enabled', 'scope_pattern',
                        'condition', 'conclusion_text', 'severity'}
REQUIRED_CONDITION_FIELDS = {'metric', 'operator', 'value'}

# Error message from implementation_specification.md §9
ERROR_RULE_FILE = (
    "The rule file (engineering_rules.json) could not be loaded due to a "
    "formatting error: {error_detail}. The default rule set will be used "
    "instead."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rules(rule_file_path: str) -> List[Dict[str, Any]]:
    """Load and validate the engineering rules JSON file.

    FR-041: Maintain a human-editable rule file.
    FR-048: Validate rule file syntax on load; report a clear error
    without crashing if malformed.

    Args:
        rule_file_path: Path to engineering_rules.json.

    Returns:
        List of valid rule dicts (malformed rules are skipped with a warning).

    Raises:
        ValueError: If the file cannot be parsed as JSON at all.
    """
    try:
        with open(rule_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(
            ERROR_RULE_FILE.format(error_detail=str(exc))
        ) from exc

    raw_rules = data.get('rules', [])
    valid_rules = []

    for i, rule in enumerate(raw_rules):
        issues = _validate_rule(rule, index=i)
        if issues:
            for issue in issues:
                logger.warning('Rule #%d (%s): %s — skipping.',
                               i, rule.get('rule_id', '?'), issue)
        else:
            valid_rules.append(rule)

    logger.info('Loaded %d valid rules from %s (%d skipped).',
                len(valid_rules), rule_file_path,
                len(raw_rules) - len(valid_rules))

    return valid_rules


def evaluate_rules(rules: List[Dict[str, Any]],
                   statistics: Dict[str, Any],
                   anomalies: Dict[str, Any],
                   df=None,
                   ) -> List[Dict[str, Any]]:
    """Evaluate all applicable rules against current session results.

    FR-043: Evaluate all applicable rules once detection completes.
    FR-044: Rules evaluate independently — no chaining.
    FR-046: Log every rule that fired.

    Rules are evaluated in the order they appear in the JSON array
    (implementation_specification.md §3).

    Args:
        rules: List of validated rule dicts from load_rules().
        statistics: Output of statistics_engine.compute_statistics().
        anomalies: Output of anomaly_detector.detect_anomalies().
        df: The cleaned DataFrame (needed for raw_value metric).

    Returns:
        List of match dicts, each with:
        - 'rule_id', 'rule_name', 'severity', 'conclusion_text',
          'recommendation_text', 'matched_on', 'column' (if scoped).
    """
    matches = []

    for rule in rules:
        # FR-045: Skip disabled rules
        if not rule.get('is_enabled', True):
            continue

        try:
            rule_matches = _evaluate_single_rule(
                rule, statistics, anomalies, df
            )
            matches.extend(rule_matches)
        except Exception as exc:
            # FR-048: Skip malformed rules, log warning, continue
            logger.warning(
                'Error evaluating rule %s: %s — skipping.',
                rule.get('rule_id', '?'), exc
            )

    logger.info('Rule evaluation complete: %d rules fired.', len(matches))
    return matches


# ---------------------------------------------------------------------------
# Rule validation (FR-048)
# ---------------------------------------------------------------------------

def _validate_rule(rule: Dict[str, Any], index: int = 0) -> List[str]:
    """Validate a single rule's structure and return a list of issues.

    Returns an empty list if the rule is valid.
    """
    issues = []

    # Check required top-level fields
    for field in REQUIRED_RULE_FIELDS:
        if field not in rule:
            issues.append(f'Missing required field: {field}')

    # Check condition fields
    condition = rule.get('condition', {})
    if not isinstance(condition, dict):
        issues.append('condition must be a dict')
    else:
        for field in REQUIRED_CONDITION_FIELDS:
            if field not in condition:
                issues.append(f'Missing condition field: {field}')

        metric = condition.get('metric')
        if metric and metric not in VALID_METRICS:
            issues.append(f'Invalid metric: {metric}')

        operator = condition.get('operator')
        if operator and operator not in VALID_OPERATORS:
            issues.append(f'Invalid operator: {operator}')

    # Check severity
    severity = rule.get('severity')
    if severity and severity not in ('Info', 'Warning', 'Critical'):
        issues.append(f'Invalid severity: {severity}')

    return issues


# ---------------------------------------------------------------------------
# Single rule evaluation
# ---------------------------------------------------------------------------

def _evaluate_single_rule(rule: Dict[str, Any],
                          statistics: Dict[str, Any],
                          anomalies: Dict[str, Any],
                          df=None) -> List[Dict[str, Any]]:
    """Evaluate a single rule against session data.

    FR-049: Rules can be scoped to specific column-name patterns
    (fnmatch semantics) or applied dataset-wide.

    Returns list of match dicts (may be multiple if rule matches
    multiple columns).
    """
    matches = []
    condition = rule['condition']
    metric = condition['metric']
    operator = condition['operator']
    value = condition['value']
    scope = rule.get('scope_pattern', '*')

    per_column_stats = statistics.get('per_column', {})

    # Determine which columns this rule applies to
    if metric == 'isolation_forest_flag':
        # Per-row evaluation, not per-column
        matches.extend(
            _eval_isolation_forest_flag(rule, anomalies, operator, value)
        )
    elif metric == 'correlation':
        # Per-pair evaluation
        matches.extend(
            _eval_correlation(rule, statistics, scope, operator, value)
        )
    elif metric == 'raw_value':
        # Per-data-point evaluation
        if df is not None:
            matches.extend(
                _eval_raw_value(rule, df, scope, operator, value)
            )
    else:
        # Per-column metrics: mean, std_dev, trend_slope,
        # coefficient_of_variation, anomaly_count
        scoped_cols = _get_scoped_columns(scope, list(per_column_stats.keys()))

        for col in scoped_cols:
            col_stats = per_column_stats.get(col, {})
            matched = _eval_column_metric(
                metric, col_stats, col, anomalies, operator, value,
                condition.get('method_filter')
            )
            if matched:
                matches.append(_build_match(rule, col, matched))

    return matches


# ---------------------------------------------------------------------------
# Metric-specific evaluators
# ---------------------------------------------------------------------------

def _eval_raw_value(rule: Dict, df, scope: str,
                    operator: str, threshold) -> List[Dict]:
    """Evaluate raw_value metric: check every data point in scoped columns.

    FR-037: Detect threshold breaches against engineering limits.
    """
    matches = []
    import pandas as pd

    scoped_cols = _get_scoped_columns(scope, list(df.columns))

    for col in scoped_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        for idx, val in df[col].dropna().items():
            if _compare(float(val), operator, threshold):
                matched_on = (
                    f'{col} = {val} at row {idx} '
                    f'{operator} {threshold}'
                )
                matches.append(_build_match(rule, col, matched_on,
                                            row_reference=int(idx)))

    return matches


def _eval_isolation_forest_flag(rule: Dict, anomalies: Dict,
                                operator: str, value) -> List[Dict]:
    """Evaluate isolation_forest_flag metric: per-row boolean check.

    implementation_specification.md §3: evaluated per-row, not per-column.
    """
    matches = []
    if_flags = anomalies.get('isolation_forest_flags', {})

    for row_idx, flag in if_flags.items():
        if _compare(flag, operator, value):
            matched_on = f'Row {row_idx} flagged by Isolation Forest'
            matches.append(_build_match(rule, '*', matched_on,
                                        row_reference=row_idx))

    return matches


def _eval_correlation(rule: Dict, statistics: Dict,
                      scope: str, operator: str, threshold) -> List[Dict]:
    """Evaluate correlation metric: per strong-pair check.

    implementation_specification.md §3: fires once per correlated pair.
    """
    matches = []
    strong_pairs = statistics.get('correlations', {}).get('strong_pairs', [])

    for pair in strong_pairs:
        col_a = pair['column_a']
        col_b = pair['column_b']
        r = abs(pair['r_value'])

        # Check if either column matches the scope
        a_match = fnmatch.fnmatch(col_a, scope)
        b_match = fnmatch.fnmatch(col_b, scope)

        if a_match or b_match:
            if _compare(r, operator, threshold):
                matched_on = (
                    f'|r| between {col_a} and {col_b} = '
                    f'{pair["r_value"]:.4f} {operator} {threshold}'
                )
                col_label = f'{col_a},{col_b}'
                matches.append(_build_match(rule, col_label, matched_on))

    return matches


def _eval_column_metric(metric: str, col_stats: Dict, col: str,
                        anomalies: Dict, operator: str, threshold,
                        method_filter: Optional[str] = None
                        ) -> Optional[str]:
    """Evaluate a column-level metric and return matched_on text if it fires."""

    actual_value = None

    if metric == 'mean':
        actual_value = col_stats.get('mean')
    elif metric == 'std_dev':
        actual_value = col_stats.get('std_dev')
    elif metric == 'trend_slope':
        actual_value = col_stats.get('trend_slope')
    elif metric == 'coefficient_of_variation':
        mean = col_stats.get('mean')
        std = col_stats.get('std_dev')
        if mean and std and mean != 0:
            actual_value = abs(std / mean)
        else:
            return None
    elif metric == 'anomaly_count':
        # Count anomalies for this column, optionally filtered by method
        anomaly_list = anomalies.get('anomalies', [])
        count = 0
        for a in anomaly_list:
            a_col = a.get('column_name', '')
            # For multivariate (IF), column_name is comma-separated
            if col in a_col.split(','):
                if method_filter is None or a.get('method') == method_filter:
                    count += 1
        actual_value = count
    else:
        return None

    if actual_value is None:
        return None

    if _compare(actual_value, operator, threshold):
        return (
            f'{metric}({col}) = {actual_value:.4f} '
            f'{operator} {threshold}'
        )
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_scoped_columns(scope: str, all_columns: List[str]) -> List[str]:
    """Return columns matching a fnmatch scope pattern (FR-049)."""
    return [col for col in all_columns if fnmatch.fnmatch(col, scope)]


def _compare(actual, operator: str, expected) -> bool:
    """Compare actual vs expected using the given operator."""
    if actual is None:
        return False
    try:
        if operator == '>':
            return actual > expected
        elif operator == '>=':
            return actual >= expected
        elif operator == '<':
            return actual < expected
        elif operator == '<=':
            return actual <= expected
        elif operator == '==':
            return actual == expected
        elif operator == '!=':
            return actual != expected
    except TypeError:
        return False
    return False


def _build_match(rule: Dict, column: str, matched_on: str,
                 row_reference: Optional[int] = None) -> Dict[str, Any]:
    """Build a standardized match result dict."""
    return {
        'rule_id': rule['rule_id'],
        'rule_name': rule['rule_name'],
        'severity': rule['severity'],
        'conclusion_text': rule['conclusion_text'],
        'recommendation_text': rule.get('recommendation_text'),
        'matched_on': matched_on,
        'column': column,
        'row_reference': row_reference,
    }
