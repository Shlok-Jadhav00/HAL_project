-- 1. Datasets Table (FR-010)
CREATE TABLE datasets (
    dataset_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT NOT NULL,
    source_path     TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (file_type IN ('CSV', 'XLSX', 'JSON', 'TXT', 'LOG')),
    row_count       INTEGER NOT NULL,
    column_count    INTEGER NOT NULL,
    imported_on     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Metadata only: the original file itself is never copied into AEIA's storage (FR-020, FR-103)

-- 2. Sessions Table (FR-098)
CREATE TABLE sessions (
    session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id      INTEGER NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    started_on      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_on    TIMESTAMP,
    findings_count  INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'In Progress' CHECK (status IN ('In Progress', 'Completed', 'Failed'))
);

-- 3. Statistical Results Table (FR-021 - FR-028)
CREATE TABLE statistical_results (
    result_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    column_name     TEXT NOT NULL,
    mean            REAL,
    median          REAL,
    mode            REAL,
    std_dev         REAL,
    variance        REAL,
    min_value       REAL,
    max_value       REAL,
    q1              REAL,
    q3              REAL,
    iqr             REAL,
    trend_slope     REAL,
    extra_json      TEXT  -- correlation matrix entries, frequency distributions, etc.
);

-- 4. Anomalies Table (FR-031 - FR-039)
CREATE TABLE anomalies (
    anomaly_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    column_name     TEXT NOT NULL,
    row_reference   INTEGER NOT NULL,
    method          TEXT NOT NULL CHECK (method IN ('ZScore', 'IQR', 'IsolationForest', 'ThresholdBreach')),
    severity        TEXT NOT NULL CHECK (severity IN ('Info', 'Warning', 'Critical')),
    value           REAL,
    is_false_positive BOOLEAN NOT NULL DEFAULT FALSE  -- FR-039
);

-- 5. Patterns Table (FR-036, FR-025, FR-026)
CREATE TABLE patterns (
    pattern_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    pattern_type    TEXT NOT NULL CHECK (pattern_type IN ('Trend', 'Correlation', 'Cyclical', 'StepChange')),
    columns_involved TEXT NOT NULL,  -- comma-separated column names
    description     TEXT,
    strength        REAL  -- e.g. correlation coefficient or slope magnitude
);

-- 6. Rule Definitions Table (FR-041 - FR-049; cached copy of engineering_rules.json)
CREATE TABLE rule_definitions (
    rule_id         TEXT PRIMARY KEY,
    rule_name       TEXT NOT NULL,
    condition_json  TEXT NOT NULL,   -- serialized condition (e.g. std_dev > threshold)
    conclusion_text TEXT NOT NULL,
    recommendation_text TEXT,
    scope_pattern   TEXT,            -- optional column-name pattern this rule applies to
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE
);

-- 7. Rule Matches Table (FR-043, FR-046)
CREATE TABLE rule_matches (
    match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL REFERENCES rule_definitions(rule_id),
    matched_on      TEXT,  -- which statistic/anomaly triggered the rule
    matched_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Insights Table (FR-051 - FR-058)
CREATE TABLE insights (
    insight_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    source_type     TEXT NOT NULL CHECK (source_type IN ('Statistic', 'Anomaly', 'Rule')),
    source_id       INTEGER,  -- FK into statistical_results / anomalies / rule_matches, depending on source_type
    text            TEXT NOT NULL
);

-- 9. Recommendations Table (FR-059 - FR-065)
CREATE TABLE recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('Info', 'Warning', 'Critical')),
    source_rule_id  TEXT REFERENCES rule_definitions(rule_id),
    engineer_note   TEXT  -- free-text annotation added by the user (FR-062)
);

-- 10. Reports Table (FR-071 - FR-080)
CREATE TABLE reports (
    report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    format          TEXT NOT NULL DEFAULT 'PDF' CHECK (format IN ('PDF', 'CSV')),
    generated_on    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    included_charts BOOLEAN NOT NULL DEFAULT TRUE
);

-- 11. App Settings Table (FR-091 - FR-097; mirrors settings.json for fast GUI lookups)
CREATE TABLE app_settings (
    setting_key     TEXT PRIMARY KEY,
    setting_value   TEXT NOT NULL,
    updated_on      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- e.g. rows: ('zscore_threshold', '3.0'), ('iqr_multiplier', '1.5'),
--            ('correlation_threshold', '0.7'), ('default_report_folder', 'C:\Users\...\AEIA\reports')
