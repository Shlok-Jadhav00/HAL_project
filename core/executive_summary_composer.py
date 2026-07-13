"""
AEIA — Executive Summary Composer (Module 6b)

Transforms raw Finding objects into professional engineering prose using
a four-stage deterministic NLP pipeline:

    Stage 1: Classify & group findings into narrative categories
    Stage 2: Select paragraph-level engineering narrative templates
    Stage 3: spaCy-assisted linguistic post-processing
    Stage 4: Assemble final summary with traceability metadata

No generative LLM is used anywhere — only pre-authored templates +
deterministic NLP transforms. Every sentence traces back to one or more
Finding objects (NFR-006).

FR-055: Template-based NLG with NLTK/spaCy-assisted phrasing.
FR-059: Synthesize all findings into an overall Engineering Conclusion.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger('aeia.executive_summary_composer')


# ---------------------------------------------------------------------------
# Column-name humanizer
# ---------------------------------------------------------------------------

# Common engineering abbreviations and their expansions
_ABBREVIATION_MAP = {
    'temp': 'temperature',
    'psi': 'psi',
    'rpm': 'RPM',
    'mm': 'mm',
    'c': '°C',
    'f': '°F',
    'k': 'K',
    'kpa': 'kPa',
    'mpa': 'MPa',
    'hz': 'Hz',
    'khz': 'kHz',
    'v': 'V',
    'ma': 'mA',
    'pct': '%',
    'avg': 'average',
    'std': 'standard deviation',
    'max': 'maximum',
    'min': 'minimum',
    'vel': 'velocity',
    'accel': 'acceleration',
    'freq': 'frequency',
    'amp': 'amplitude',
    'press': 'pressure',
    'vol': 'volume',
    'dia': 'diameter',
    'len': 'length',
    'wt': 'weight',
    'alt': 'altitude',
    'lat': 'latitude',
    'lon': 'longitude',
    'vib': 'vibration',
    'id': 'ID',
    's': '',  # seconds unit suffix (often in mm_s = mm/s)
}

# Units that should appear after the humanized name, not inline
_UNIT_SUFFIXES = {'°C', '°F', 'K', 'psi', 'kPa', 'MPa', 'Hz', 'kHz',
                  'V', 'mA', 'mm', 'RPM', '%'}


def humanize_column_name(col_name: str) -> str:
    """Convert a column name like 'Engine_Temp_C' to 'engine temperature (Engine_Temp_C)'.

    Rules:
    - Split on underscores and camelCase boundaries
    - Expand known abbreviations
    - Detect trailing unit tokens (C, psi, mm_s) and separate them
    - Return: 'humanized label (OriginalName)'
    """
    # Special case: single-word names that are themselves a known term
    if col_name in _ABBREVIATION_MAP.values() or col_name.upper() == col_name:
        lower = col_name.lower()
        if lower in _ABBREVIATION_MAP:
            expanded = _ABBREVIATION_MAP[lower]
            if expanded:
                return f"{expanded} ({col_name})"
        return f"{col_name.lower()} ({col_name})"

    # Split on underscores
    parts = col_name.split('_')

    # Expand abbreviations and build readable tokens
    readable = []
    unit_parts = []
    for i, part in enumerate(parts):
        lower = part.lower()
        if lower in _ABBREVIATION_MAP:
            expanded = _ABBREVIATION_MAP[lower]
            # Skip empty expansions (like 's' -> '')
            if not expanded:
                continue
            # If it's a unit suffix and it's near the end, treat as unit
            if expanded in _UNIT_SUFFIXES and i >= len(parts) - 2:
                unit_parts.append(expanded)
            else:
                readable.append(expanded)
        else:
            # CamelCase split
            tokens = re.sub(r'([a-z])([A-Z])', r'\1 \2', part).split()
            readable.extend(t.lower() for t in tokens)

    # Build the humanized label
    label = ' '.join(readable).strip()

    # Clean up: collapse multiple spaces
    label = re.sub(r'\s+', ' ', label).strip()

    if not label:
        label = col_name.lower()

    return f"{label} ({col_name})"


def _humanize_column_list(columns: List[str]) -> str:
    """Humanize a list of column names into a readable English list."""
    if not columns:
        return ''
    labels = [humanize_column_name(c) for c in columns]
    if len(labels) == 1:
        return labels[0]
    elif len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    else:
        return ', '.join(labels[:-1]) + f", and {labels[-1]}"


# ---------------------------------------------------------------------------
# Stage 1: Classify & Group Findings
# ---------------------------------------------------------------------------

# Narrative categories — ordered by severity priority for paragraph ordering
NARRATIVE_CATEGORIES = [
    'safety_breach',
    'anomaly_event',
    'operational_stability',
    'drift_trend',
    'system_pattern',
    'channel_relationship',
]


def _classify_finding(finding: Dict[str, Any]) -> str:
    """Classify a single finding into a narrative category.

    Mapping logic:
    - Critical severity + any type → safety_breach
    - ZScore/IQR with Warning severity → anomaly_event
    - IsolationForest → system_pattern
    - Trend → drift_trend
    - Correlation → channel_relationship
    - Rule matches about variance/instability → operational_stability
    - Rule matches (general Warning) → anomaly_event
    """
    severity = finding.get('severity', 'Info')
    finding_type = finding.get('finding_type', '')
    source_type = finding.get('source_type', '')
    rule_id = finding.get('rule_id', '')

    # Critical severity always maps to safety breach
    if severity == 'Critical':
        return 'safety_breach'

    # Detection-method based classification
    if finding_type in ('ZScore', 'IQR'):
        return 'anomaly_event'
    if finding_type == 'IsolationForest':
        return 'system_pattern'
    if finding_type == 'Trend':
        return 'drift_trend'
    if finding_type == 'Correlation':
        return 'channel_relationship'

    # Rule-based classification
    if finding_type.startswith('Rule:'):
        # Variance/instability rules
        if 'variance' in rule_id.lower() or 'instability' in rule_id.lower() \
                or rule_id == 'RULE-003':
            return 'operational_stability'
        # Drift rules
        if 'drift' in rule_id.lower() or rule_id == 'RULE-002':
            return 'drift_trend'
        # Multivariate rules
        if 'multivariate' in rule_id.lower() or rule_id == 'RULE-006':
            return 'system_pattern'
        # Correlation rules
        if 'correlat' in rule_id.lower() or rule_id == 'RULE-005':
            return 'channel_relationship'
        # General warning rules
        return 'anomaly_event'

    return 'anomaly_event'


def _group_findings(all_insights: List[Dict[str, Any]]
                    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Group findings by narrative category, then by column.

    Returns:
        {category: {column: [finding, ...]}}
    """
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for finding in all_insights:
        category = _classify_finding(finding)
        col = finding.get('column', 'General')

        if category not in grouped:
            grouped[category] = {}
        if col not in grouped[category]:
            grouped[category][col] = []
        grouped[category][col].append(finding)

    return grouped


# ---------------------------------------------------------------------------
# Stage 2: Engineering Narrative Templates
# ---------------------------------------------------------------------------

# Paragraph-level templates organized by narrative category.
# Each template uses {named_placeholders} filled from merged finding data.
# Templates describe WHAT HAPPENED and WHAT IT MEANS, not HOW the math works.

OVERALL_ASSESSMENT_TEMPLATES = {
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


def _build_paragraph(category: str,
                     column_findings: Dict[str, List[Dict[str, Any]]],
                     ) -> List[Dict[str, Any]]:
    """Build narrative paragraphs for a single category.

    Returns a list of paragraph dicts, each with:
        - 'text': the paragraph prose
        - 'source_findings': list of finding references
        - 'narrative_category': the category name
    """
    paragraphs = []
    columns = list(column_findings.keys())

    if not columns:
        return paragraphs

    templates = NARRATIVE_TEMPLATES.get(category, {})
    if isinstance(templates, str):
        # Category has only a single template (like 'no_findings')
        return [{
            'text': templates,
            'source_findings': [],
            'narrative_category': category,
        }]

    # Decide single vs. multi based on column count
    if len(columns) == 1:
        col = columns[0]
        findings = column_findings[col]
        text = _render_single_column(category, col, findings, templates)
        paragraphs.append({
            'text': text,
            'source_findings': _extract_sources(findings),
            'narrative_category': category,
        })
    else:
        # Check if we should produce per-column paragraphs or one merged
        # For safety breaches and anomalies, per-column is clearer
        if category in ('safety_breach', 'anomaly_event', 'drift_trend',
                        'operational_stability'):
            for col in columns:
                findings = column_findings[col]
                text = _render_single_column(
                    category, col, findings, templates
                )
                paragraphs.append({
                    'text': text,
                    'source_findings': _extract_sources(findings),
                    'narrative_category': category,
                })
        else:
            # Merged paragraph for relationships and patterns
            all_findings = []
            for findings in column_findings.values():
                all_findings.extend(findings)
            text = _render_multi_column(
                category, column_findings, templates
            )
            paragraphs.append({
                'text': text,
                'source_findings': _extract_sources(all_findings),
                'narrative_category': category,
            })

    return paragraphs


def _render_single_column(category: str, col: str,
                          findings: List[Dict[str, Any]],
                          templates: Dict[str, str]) -> str:
    """Render a single-column paragraph using the 'single' template."""
    template = templates.get('single', '')
    if not template:
        return ''

    column_label = humanize_column_name(col)

    # Extract representative data from findings — look across all
    # finding dicts including the raw anomaly data carried forward
    values = []
    rows = []
    for f in findings:
        v = f.get('value')
        if v is not None and v != '':
            values.append(v)
        r = f.get('row_reference')
        if r is not None and str(r) not in rows:
            rows.append(str(r))
        # Also check the text for embedded values
        if not values:
            text = f.get('text', '')
            val_match = re.search(r'(?:value of|=)\s*([\d.]+)', text)
            if val_match:
                values.append(val_match.group(1))
        if not rows or rows == ['']:
            text = f.get('text', '')
            row_match = re.search(r'at row (\d+)', text)
            if row_match:
                rows.append(row_match.group(1))

    # Deduplicate rows
    rows = list(dict.fromkeys(rows))  # preserve order, remove dupes

    # Determine event type for safety breaches
    event_type = _infer_event_type(col, findings)

    # Look for threshold from rule matches
    threshold_detail = ''
    for f in findings:
        if f.get('source_type') == 'Rule':
            matched_on = f.get('text', '')
            threshold_match = re.search(r'threshold\s+(?:of\s+)?(\d+)', matched_on)
            if threshold_match:
                threshold_detail = f" of {threshold_match.group(1)}"
                break
            # Also look for '> NNN' pattern in the rule text
            gt_match = re.search(r'> (\d+)', matched_on)
            if gt_match:
                threshold_detail = f" of {gt_match.group(1)}"
                break

    # Unit hint — don't append if already in label
    unit_hint = _extract_unit_hint(col)

    # Direction for trends
    direction = 'upward'
    for f in findings:
        text = f.get('text', '').lower()
        if 'decreasing' in text:
            direction = 'downward'
        elif 'increasing' in text:
            direction = 'upward'

    # Correlation-specific fields
    col_a_label = column_label
    col_b_label = ''
    if category == 'channel_relationship':
        # Column name for correlations is 'ColA,ColB'
        parts = col.split(',')
        if len(parts) == 2:
            col_a_label = humanize_column_name(parts[0].strip())
            col_b_label = humanize_column_name(parts[1].strip())

    row_refs = ', '.join(rows[:5]) if rows else 'multiple points'
    value_str = str(values[0]) if values else 'an extreme value'

    try:
        text = template.format(
            column_label=column_label,
            event_type=event_type,
            value=value_str,
            unit_hint=unit_hint,
            row_ref=rows[0] if rows else '?',
            row_refs=row_refs,
            count=len(findings),
            threshold_detail=threshold_detail,
            direction=direction,
            col_a_label=col_a_label,
            col_b_label=col_b_label,
            channel_list=column_label,
        )
    except (KeyError, IndexError):
        # Graceful fallback if template has unexpected placeholders
        text = f"Findings were detected in the {column_label} channel."

    return text


def _render_multi_column(category: str,
                         column_findings: Dict[str, List[Dict[str, Any]]],
                         templates: Dict[str, str]) -> str:
    """Render a multi-column paragraph using the 'multi' template."""
    template = templates.get('multi', '')
    if not template:
        return ''

    columns = list(column_findings.keys())
    all_findings = []
    all_rows = []
    for findings in column_findings.values():
        all_findings.extend(findings)
        for f in findings:
            r = f.get('row_reference')
            if r is not None:
                all_rows.append(str(r))

    channel_list = _humanize_column_list(columns)
    row_refs = ', '.join(sorted(set(all_rows))[:5]) if all_rows else 'multiple points'

    # For correlations, extract pair labels
    col_a_label = ''
    col_b_label = ''
    if category == 'channel_relationship' and columns:
        parts = columns[0].split(',')
        if len(parts) == 2:
            col_a_label = humanize_column_name(parts[0].strip())
            col_b_label = humanize_column_name(parts[1].strip())

    try:
        text = template.format(
            count=len(columns),
            channel_list=channel_list,
            row_refs=row_refs,
            col_a_label=col_a_label,
            col_b_label=col_b_label,
        )
    except (KeyError, IndexError):
        text = f"Findings were detected across {len(columns)} channels."

    return text


def _infer_event_type(col: str, findings: List[Dict[str, Any]]) -> str:
    """Infer a human-readable event type from the column name and findings."""
    col_lower = col.lower()
    if 'temp' in col_lower:
        return 'overheating event'
    elif 'press' in col_lower:
        return 'pressure exceedance'
    elif 'vib' in col_lower:
        return 'vibration spike'
    elif 'rpm' in col_lower or 'speed' in col_lower:
        return 'rotational speed exceedance'
    elif 'volt' in col_lower or 'current' in col_lower:
        return 'electrical parameter exceedance'
    elif 'flow' in col_lower:
        return 'flow rate anomaly'
    else:
        return 'parameter exceedance'


def _extract_unit_hint(col: str) -> str:
    """Extract a unit hint string from the column name for inline use."""
    parts = col.split('_')
    if len(parts) >= 2:
        last = parts[-1].lower()
        if last in _ABBREVIATION_MAP:
            unit = _ABBREVIATION_MAP[last]
            if unit in _UNIT_SUFFIXES:
                return f" {unit}"
    return ''


def _extract_sources(findings: List[Dict[str, Any]]
                     ) -> List[Dict[str, Any]]:
    """Extract traceability source references from findings."""
    sources = []
    for f in findings:
        sources.append({
            'finding_type': f.get('finding_type', ''),
            'column': f.get('column', ''),
            'severity': f.get('severity', 'Info'),
            'rule_id': f.get('rule_id'),
        })
    return sources


# ---------------------------------------------------------------------------
# Stage 3: spaCy NLP Post-Processing
# ---------------------------------------------------------------------------

# Lazy-loaded spaCy model to avoid import-time costs
_nlp = None


def _get_nlp():
    """Lazy-load the spaCy English model.

    Uses en_core_web_sm (statistical, ~12 MB, CPU-only).
    Falls back gracefully if spaCy is not installed.
    """
    global _nlp
    if _nlp is not None:
        return _nlp

    try:
        import spacy
        try:
            _nlp = spacy.load('en_core_web_sm')
        except OSError:
            # Model not downloaded — use blank English pipeline
            logger.warning(
                'spaCy en_core_web_sm model not found. '
                'Using blank pipeline — some NLP features disabled. '
                'Run: python -m spacy download en_core_web_sm'
            )
            _nlp = spacy.blank('en')
            _nlp.add_pipe('sentencizer')
    except ImportError:
        logger.warning(
            'spaCy not installed. NLP post-processing disabled. '
            'Executive summary will still be generated from templates.'
        )
        _nlp = None

    return _nlp


# Discourse connectors for same-severity transitions
_SAME_SEVERITY_CONNECTORS = [
    'Additionally, ',
    'Furthermore, ',
    'In the same analysis period, ',
    'Similarly, ',
]

# Discourse connectors for cross-severity transitions
_CROSS_SEVERITY_CONNECTORS = [
    'Separately, ',
    'On a related note, ',
    'In addition to the above, ',
    'Beyond the critical findings, ',
]


def _apply_nlp_postprocessing(paragraphs: List[Dict[str, Any]]
                              ) -> List[Dict[str, Any]]:
    """Apply spaCy-based linguistic improvements to assembled paragraphs.

    Stage 3a: Referring expression generation (pronoun resolution)
    Stage 3b: Sentence boundary smoothing (discourse connectors)
    Stage 3c: Redundancy elimination

    All operations are deterministic — same input → same output.
    """
    nlp = _get_nlp()
    if nlp is None or len(paragraphs) <= 1:
        return paragraphs

    # 3a: Referring expression generation
    paragraphs = _resolve_referring_expressions(paragraphs, nlp)

    # 3b: Sentence boundary smoothing (add connectors between paragraphs)
    paragraphs = _add_discourse_connectors(paragraphs)

    # 3c: Redundancy elimination
    paragraphs = _eliminate_redundancy(paragraphs, nlp)

    return paragraphs


def _resolve_referring_expressions(paragraphs: List[Dict[str, Any]],
                                   nlp) -> List[Dict[str, Any]]:
    """Replace repeated column names with contextual references.

    If consecutive paragraphs mention the same column, the second
    occurrence is replaced with 'this channel', 'this parameter', etc.
    """
    _REFERENCES = ['this channel', 'this parameter', 'the same sensor']

    prev_column = None
    for i, para in enumerate(paragraphs):
        if i == 0:
            # Extract primary column from first paragraph
            sources = para.get('source_findings', [])
            if sources:
                prev_column = sources[0].get('column', '')
            continue

        sources = para.get('source_findings', [])
        if not sources:
            continue

        current_column = sources[0].get('column', '')
        if current_column and current_column == prev_column:
            # Replace the humanized column name with a reference
            humanized = humanize_column_name(current_column)
            text = para['text']
            ref = _REFERENCES[i % len(_REFERENCES)]
            # Only replace the first occurrence to keep readability
            if humanized in text:
                text = text.replace(humanized, ref, 1)
                para['text'] = text
            # Also handle 'the <column_label> channel' -> 'this channel'
            # to avoid 'the this channel channel'
            text = para['text']
            text = text.replace(f'the {ref} channel', f'{ref}')
            text = text.replace(f'The {ref} channel', ref[0].upper() + ref[1:])
            para['text'] = text

        prev_column = current_column

    return paragraphs


def _add_discourse_connectors(paragraphs: List[Dict[str, Any]]
                              ) -> List[Dict[str, Any]]:
    """Insert discourse connectors between paragraphs of different categories.

    Connectors are selected deterministically by ordinal position.
    """
    if len(paragraphs) <= 1:
        return paragraphs

    prev_category = paragraphs[0].get('narrative_category', '')
    connector_idx = 0

    for i in range(1, len(paragraphs)):
        current_category = paragraphs[i].get('narrative_category', '')
        text = paragraphs[i]['text']

        # Don't add connectors to closing paragraphs
        if current_category == 'closing':
            continue

        # Select connector based on whether category changed
        if current_category == prev_category:
            connector = _SAME_SEVERITY_CONNECTORS[
                connector_idx % len(_SAME_SEVERITY_CONNECTORS)
            ]
        else:
            connector = _CROSS_SEVERITY_CONNECTORS[
                connector_idx % len(_CROSS_SEVERITY_CONNECTORS)
            ]

        # Prepend connector — lowercase the first character of the paragraph
        if text and text[0].isupper():
            text = connector + text[0].lower() + text[1:]
        else:
            text = connector + text

        paragraphs[i]['text'] = text
        prev_category = current_category
        connector_idx += 1

    return paragraphs


def _eliminate_redundancy(paragraphs: List[Dict[str, Any]],
                          nlp) -> List[Dict[str, Any]]:
    """Remove paragraphs that are semantically redundant.

    Two paragraphs are considered redundant if:
    - They reference the same column
    - Their noun chunks overlap by >70%

    In that case, the lower-severity paragraph is removed.
    """
    if len(paragraphs) <= 1:
        return paragraphs

    # Extract noun chunks for each paragraph
    chunk_sets = []
    for para in paragraphs:
        doc = nlp(para['text'])
        if hasattr(doc, 'noun_chunks'):
            chunks = {chunk.root.lemma_.lower() for chunk in doc.noun_chunks}
        else:
            # Fallback: use simple word tokens
            chunks = {t.lower() for t in para['text'].split()
                      if len(t) > 3}
        chunk_sets.append(chunks)

    # Find redundant pairs
    to_remove = set()
    for i in range(len(paragraphs)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(paragraphs)):
            if j in to_remove:
                continue

            # Check same column
            col_i = _get_primary_column(paragraphs[i])
            col_j = _get_primary_column(paragraphs[j])
            if not col_i or not col_j or col_i != col_j:
                continue

            # Check noun chunk overlap
            if not chunk_sets[i] or not chunk_sets[j]:
                continue
            overlap = chunk_sets[i] & chunk_sets[j]
            smaller = min(len(chunk_sets[i]), len(chunk_sets[j]))
            if smaller > 0 and len(overlap) / smaller > 0.7:
                # Remove the lower-severity one
                sev_i = _get_max_severity(paragraphs[i])
                sev_j = _get_max_severity(paragraphs[j])
                if _SEVERITY_RANK.get(sev_j, 2) > _SEVERITY_RANK.get(sev_i, 2):
                    to_remove.add(j)
                else:
                    to_remove.add(i)

    return [p for idx, p in enumerate(paragraphs) if idx not in to_remove]


_SEVERITY_RANK = {'Critical': 0, 'Warning': 1, 'Info': 2}


def _get_primary_column(paragraph: Dict[str, Any]) -> str:
    """Get the primary column from a paragraph's source findings."""
    sources = paragraph.get('source_findings', [])
    if sources:
        return sources[0].get('column', '')
    return ''


def _get_max_severity(paragraph: Dict[str, Any]) -> str:
    """Get the highest severity from a paragraph's source findings."""
    sources = paragraph.get('source_findings', [])
    best = 'Info'
    for s in sources:
        sev = s.get('severity', 'Info')
        if _SEVERITY_RANK.get(sev, 2) < _SEVERITY_RANK.get(best, 2):
            best = sev
    return best


# ---------------------------------------------------------------------------
# Stage 4: Assemble Final Summary
# ---------------------------------------------------------------------------

def compose_executive_summary(insights: Dict[str, Any],
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
    
    full_text = '\n\n'.join(p['text'] for p in paragraphs)
    logger.info('Composed executive summary: %d paragraphs from %d findings.', len(paragraphs), len(all_insights))
    
    return {
        'text': full_text,
        'paragraphs': paragraphs,
    }
