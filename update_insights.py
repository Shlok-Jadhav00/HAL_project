import os
import re

filepath = r'e:\AEIA\core\insight_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

confidence_matrix_code = '''
def _apply_confidence_matrix(all_insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    \"\"\"Apply the confidence-based severity prioritization (Confidence Matrix).

    FR-038: Prioritize findings dynamically based on overlapping evidence.
    \"\"\"
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
    for (col, row), group in row_findings.items():
        stat_detectors = [f for f in group if f.get('source_type') in ('Statistic', 'Anomaly')]
        rule_detectors = [f for f in group if f.get('source_type') == 'Rule']

        has_stats = len(stat_detectors) > 0
        multiple_stats = len(stat_detectors) > 1
        has_rules = len(rule_detectors) > 0

        # Check for hardcoded critical rules (Option B)
        has_hard_critical = any(r.get('raw_severity') == 'Critical' for r in rule_detectors)

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

        for insight in group:
            if insight.get('raw_severity') == 'Critical' and insight.get('source_type') == 'Rule':
                insight['severity'] = 'Critical'
            else:
                insight['severity'] = new_severity

            # Update the text to reflect the new severity if it's in the text
            text = insight.get('text', '')
            insight['text'] = re.sub(r'\((Info|Warning|Critical)\)', f'({insight["severity"]})', text)

    return all_insights
'''

# Find the place to insert _apply_confidence_matrix
insert_idx = content.find('def regenerate_insights')
content = content[:insert_idx] + confidence_matrix_code + '\n\n' + content[insert_idx:]

# Update generate_insights to call _apply_confidence_matrix
content = content.replace(
    'all_insights = anomaly_insights + pattern_insights + rule_insights',
    'all_insights = anomaly_insights + pattern_insights + rule_insights\n    all_insights = _apply_confidence_matrix(all_insights)'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated core/insight_generator.py with Confidence Matrix logic.')
