import re
import os

filepath = r'e:\AEIA\core\executive_summary_composer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We want to replace NARRATIVE_TEMPLATES
new_templates = '''OVERALL_ASSESSMENT_TEMPLATES = {
    'Critical': (
        "The analysis indicates a critical operating condition requiring "
        "immediate investigation before continued operation. The primary "
        "concern is {primary_concern}. Prompt corrective action is recommended."
    ),
    'Warning': (
        "The analysis indicates degraded operating conditions. While no "
        "immediate safety-critical condition was identified, the detected "
        "abnormalities should be investigated during the next maintenance "
        "or inspection cycle."
    ),
    'Info': (
        "The analysed system operated within expected engineering limits. "
        "The recorded observations are informational and do not currently "
        "indicate any significant operational concern."
    )
}

NARRATIVE_TEMPLATES = {
    'safety_breach': {
        'single': "A critical safety-limit breach was detected in the {column_label} channel.",
        'multi': "Critical safety-limit breaches were identified across {count} channels ({channel_list})."
    },
    'anomaly_event': {
        'single': "An anomalous reading was identified in the {column_label} channel.",
        'multi': "Anomalous readings were identified across {count} channels ({channel_list})."
    },
    'drift_trend': {
        'single': "A sustained {direction} trend was observed in the {column_label} channel.",
        'multi': "Sustained trends were observed across {count} channels ({channel_list})."
    },
    'operational_stability': {
        'single': "The {column_label} channel exhibited unusually high variability, suggesting possible mechanical instability.",
        'multi': "Elevated variability was observed across {count} channels ({channel_list}), suggesting possible instability."
    },
    'system_pattern': {
        'single': "A multivariate anomaly was detected, indicating an unusual combination of operating states.",
        'multi': "Multivariate anomalies were detected, indicating an unusual combination of operating states."
    },
    'channel_relationship': {
        'single': "An unexpected correlation was observed involving the {column_label} channel.",
        'multi': "Unexpected correlations were observed involving {count} channels ({channel_list})."
    }
}
'''

# Find NARRATIVE_TEMPLATES block to replace
start_idx = content.find('NARRATIVE_TEMPLATES = {')
end_idx = content.find('def _build_paragraph')
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_templates + '\n\n' + content[end_idx:]

# Rewrite compose_executive_summary
new_compose = '''def compose_executive_summary(insights: Dict[str, Any],
                              statistics: Optional[Dict[str, Any]] = None,
                              dataset_info: Optional[Dict[str, Any]] = None,
                              ) -> Dict[str, Any]:
    """Compose a professional engineering Executive Summary from findings.

    FR-055: Template-based NLG with spaCy-assisted phrasing.
    FR-059: Synthesize all findings into an overall Engineering Conclusion.
    NFR-006: Every paragraph traces to source Finding objects.
    """
    all_insights = insights.get('all_insights', [])
    
    # Overview (Paragraph 1)
    total_cols = dataset_info.get('column_count', len(statistics.get('per_column', {})) if statistics else 0) if dataset_info else 0
    total_rows = dataset_info.get('row_count', 0) if dataset_info else 0
    
    channels_with_issues = {f.get('column') for f in all_insights if f.get('severity') in ('Critical', 'Warning')}
    all_channels = list(statistics.get('per_column', {}).keys()) if statistics else []
    healthy_channels = [c for c in all_channels if c not in channels_with_issues and c != 'Sample_ID']
    
    healthy_str = ""
    if healthy_channels:
        if len(healthy_channels) == 1:
            healthy_str = f", including {humanize_column_name(healthy_channels[0])},"
        else:
            healthy_str = f", including {humanize_column_name(healthy_channels[0])} and {humanize_column_name(healthy_channels[1])},"
            
    para1_text = (
        f"Analysis was conducted on a dataset comprising {total_rows} samples "
        f"across {total_cols} measurement channels. The majority of parameters{healthy_str} "
        "operated within expected engineering limits throughout the recording period."
    )
    
    para1 = {
        'text': para1_text,
        'source_findings': [],
        'narrative_category': 'overview'
    }
    
    # Synthesis (Paragraph 2)
    grouped = _group_findings(all_insights)
    para2_sentences = []
    para2_sources = []
    
    if not all_insights or not any(sev in [f.get('severity') for f in all_insights] for sev in ('Critical', 'Warning')):
        para2_sentences.append("No significant abnormalities or critical deviations were identified during the analysis.")
    else:
        para2_sentences.append("However, specific operational deviations were identified.")
        for category in NARRATIVE_CATEGORIES:
            if category in grouped:
                cat_paras = _build_paragraph(category, grouped[category])
                for cp in cat_paras:
                    para2_sentences.append(cp['text'])
                    para2_sources.extend(cp['source_findings'])
                    
    # Apply simple NLP referring expression resolution directly to the synthesis sentences before joining
    nlp = _get_nlp()
    if nlp is not None:
        # Resolve referring expressions in the list of sentences
        temp_paras = [{'text': s, 'source_findings': para2_sources} for s in para2_sentences[1:]]
        temp_paras = _resolve_referring_expressions(temp_paras, nlp)
        para2_sentences[1:] = [p['text'] for p in temp_paras]

    para2_text = " ".join(para2_sentences)
    para2 = {
        'text': para2_text,
        'source_findings': para2_sources,
        'narrative_category': 'synthesis'
    }
    
    # Overall Assessment (Paragraph 3)
    highest_severity = 'Info'
    if all_insights:
        highest_severity = _get_max_severity({'source_findings': all_insights})
        
    primary_concern = "anomalies in the system"
    if highest_severity == 'Critical':
        criticals = [f for f in all_insights if f.get('severity') == 'Critical']
        if criticals:
            col = criticals[0].get('column', '')
            primary_concern = f"critical deviations in the {humanize_column_name(col)} channel"
            
    para3_text = OVERALL_ASSESSMENT_TEMPLATES[highest_severity].format(
        primary_concern=primary_concern
    )
    para3 = {
        'text': para3_text,
        'source_findings': all_insights[:3],
        'narrative_category': 'assessment'
    }
    
    paragraphs = [para1, para2, para3]
    
    full_text = '\\n\\n'.join(p['text'] for p in paragraphs)
    logger.info('Composed executive summary: %d paragraphs from %d findings.', len(paragraphs), len(all_insights))
    
    return {
        'text': full_text,
        'paragraphs': paragraphs,
    }
'''

start_idx = content.find('def compose_executive_summary')
if start_idx != -1:
    content = content[:start_idx] + new_compose

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated core/executive_summary_composer.py')
