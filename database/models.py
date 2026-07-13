"""
AEIA — Lightweight Row-Mapping Classes for All 11 Database Tables

These dataclasses provide a clean Python interface for the rows returned by
SQLite queries. They are used by database/db_manager.py and consumed by
gui/ panels and core/ modules — no raw SQL outside db_manager.py.

Schema reference: database/schema.sql and docs/technical_design.md Part A.

No PyQt5 imports allowed in this module (code_hygiene_guide.md §1).
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Table 1: datasets (FR-010)
# ---------------------------------------------------------------------------
@dataclass
class DatasetRecord:
    """Metadata about an imported dataset file.

    The original file is never copied into AEIA's storage — only this
    metadata is persisted (FR-020, FR-103).
    """
    dataset_id: int
    filename: str
    source_path: str
    file_type: str          # 'CSV', 'XLSX', 'JSON', 'TXT', 'LOG'
    row_count: int
    column_count: int
    imported_on: str         # ISO timestamp string


# ---------------------------------------------------------------------------
# Table 2: sessions (FR-098)
# ---------------------------------------------------------------------------
@dataclass
class SessionRecord:
    """One analysis run linking a dataset to its results."""
    session_id: int
    dataset_id: int
    started_on: str          # ISO timestamp
    completed_on: Optional[str]
    findings_count: int
    status: str              # 'In Progress', 'Completed', 'Failed'


# ---------------------------------------------------------------------------
# Table 3: statistical_results (FR-021 – FR-028)
# ---------------------------------------------------------------------------
@dataclass
class StatisticalResultRecord:
    """Per-column statistical output for a session."""
    result_id: int
    session_id: int
    column_name: str
    mean: Optional[float]
    median: Optional[float]
    mode: Optional[float]
    std_dev: Optional[float]
    variance: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    q1: Optional[float]
    q3: Optional[float]
    iqr: Optional[float]
    trend_slope: Optional[float]
    extra_json: Optional[str]   # JSON string: correlation entries, freq dists


# ---------------------------------------------------------------------------
# Table 4: anomalies (FR-031 – FR-039)
# ---------------------------------------------------------------------------
@dataclass
class AnomalyRecord:
    """A single detected anomaly for a session."""
    anomaly_id: int
    session_id: int
    column_name: str
    row_reference: int       # Original row index / Sample_ID
    method: str              # 'ZScore', 'IQR', 'IsolationForest', 'ThresholdBreach'
    severity: str            # 'Info', 'Warning', 'Critical'
    value: Optional[float]
    is_false_positive: bool  # FR-039


# ---------------------------------------------------------------------------
# Table 5: patterns (FR-036, FR-025, FR-026)
# ---------------------------------------------------------------------------
@dataclass
class PatternRecord:
    """A detected trend, correlation, cyclical pattern, or step change."""
    pattern_id: int
    session_id: int
    pattern_type: str        # 'Trend', 'Correlation', 'Cyclical', 'StepChange'
    columns_involved: str    # Comma-separated column names
    description: Optional[str]
    strength: Optional[float]  # e.g. correlation coefficient or slope magnitude


# ---------------------------------------------------------------------------
# Table 6: rule_definitions (FR-041 – FR-049)
# ---------------------------------------------------------------------------
@dataclass
class RuleDefinitionRecord:
    """Cached copy of a rule from engineering_rules.json."""
    rule_id: str             # e.g. 'RULE-001'
    rule_name: str
    condition_json: str      # Serialized JSON condition object
    conclusion_text: str
    recommendation_text: Optional[str]
    scope_pattern: Optional[str]   # fnmatch pattern for column names
    is_enabled: bool


# ---------------------------------------------------------------------------
# Table 7: rule_matches (FR-043, FR-046)
# ---------------------------------------------------------------------------
@dataclass
class RuleMatchRecord:
    """A rule that fired for a specific session."""
    match_id: int
    session_id: int
    rule_id: str
    matched_on: Optional[str]   # Which statistic/anomaly triggered the rule
    matched_at: str              # ISO timestamp


# ---------------------------------------------------------------------------
# Table 8: insights (FR-051 – FR-058)
# ---------------------------------------------------------------------------
@dataclass
class InsightRecord:
    """A generated natural-language sentence linked to a finding."""
    insight_id: int
    session_id: int
    source_type: str         # 'Statistic', 'Anomaly', 'Rule'
    source_id: Optional[int]  # FK into the relevant table
    text: str


# ---------------------------------------------------------------------------
# Table 9: recommendations (FR-059 – FR-065)
# ---------------------------------------------------------------------------
@dataclass
class RecommendationRecord:
    """A recommended action ranked by severity."""
    recommendation_id: int
    session_id: int
    text: str
    severity: str            # 'Info', 'Warning', 'Critical'
    source_rule_id: Optional[str]  # FK to rule_definitions
    engineer_note: Optional[str]   # Free-text annotation (FR-062)


# ---------------------------------------------------------------------------
# Table 10: reports (FR-071 – FR-080)
# ---------------------------------------------------------------------------
@dataclass
class ReportRecord:
    """Metadata about an exported PDF or CSV report."""
    report_id: int
    session_id: int
    file_path: str
    format: str              # 'PDF' or 'CSV'
    generated_on: str        # ISO timestamp
    included_charts: bool


# ---------------------------------------------------------------------------
# Table 11: app_settings (FR-091 – FR-097)
# ---------------------------------------------------------------------------
@dataclass
class AppSettingRecord:
    """A single key-value setting mirroring settings.json."""
    setting_key: str
    setting_value: str
    updated_on: str          # ISO timestamp
