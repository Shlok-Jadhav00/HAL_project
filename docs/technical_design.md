# Technical Design: Database Schema & Directory Structure

This document details the database schema (`schema.sql`) and the directory layout of the AEIA codebase.

---

## Part A: Database Schema (`schema.sql`)

Below are the `CREATE TABLE` statements for the 11 tables required by AEIA. All statements are written
for **SQLite** (the embedded, file-based database used since AEIA has no separate database server).

```sql
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
```

---

## Part B: Folder and File Directory Structure

To keep the codebase maintainable by a single developer (NFR-005), AEIA uses a clean, layered structure
that mirrors the HLD's separation between GUI, core logic, and data.

```
AEIA/
│
├── main.py                       # Entry point; launches the PyQt5 application
├── requirements.txt              # Python dependencies with pinned versions (NFR-012)
│
├── config/
│   └── settings.json             # Default thresholds, folders, UI preferences (FR-095)
│
├── rules/
│   └── engineering_rules.json    # Default starter rule set (FR-047), user-editable (FR-045)
│
├── core/                         # Pure-Python analysis engines (no GUI dependencies)
│   ├── data_loader.py            # CSV/XLSX/JSON/TXT/LOG parsing & type inference (Module 1)
│   ├── preprocessor.py           # Validation, cleaning, missing values, duplicates (Module 2)
│   ├── statistics_engine.py      # Mean/median/std/quartiles/trend/correlation (Module 3)
│   ├── anomaly_detector.py       # Z-score, IQR, Isolation Forest detection (Module 4)
│   ├── expert_system.py          # Rule file loader & evaluator (Module 5)
│   ├── insight_generator.py      # Template-based NLG summaries (Module 6)
│   ├── recommendation_engine.py  # Conclusion & recommendation synthesis (Module 7)
│   ├── chart_builder.py          # Matplotlib chart generation (Module 8)
│   └── report_builder.py         # ReportLab PDF/CSV export (Module 9)
│
├── database/
│   ├── db_manager.py             # SQLite connection/session handling
│   ├── models.py                 # Lightweight row-mapping classes for all 11 tables
│   └── schema.sql                # This schema, applied on first run
│
├── gui/                          # PyQt5 presentation layer (Module 10 & 11)
│   ├── main_window.py            # Main window: sidebar navigation, tabbed sessions
│   ├── import_panel.py           # Import & preview UI
│   ├── analysis_panel.py         # Analysis results, findings review, notes
│   ├── report_panel.py           # Report preview & export UI
│   ├── history_panel.py          # Session history browser (Module 12)
│   ├── settings_dialog.py        # Threshold & rule management UI
│   └── theme.py                  # Central colour palette (see color_philosophy.md)
│
├── docs/
│   ├── AEIA_requirements_context.md
│   ├── changelog.md
│   ├── hld.md
│   ├── technical_design.md        # This document
│   ├── test_cases.md
│   ├── code_hygiene_guide.md
│   ├── color_philosophy.md
│   ├── learning_development_vs_production.md
│   ├── teaching_code_changes.md
│   ├── tech_stack_and_deployment_status.md
│   └── packaging_deployment_guide.md
│
├── tests/
│   └── test_core.py              # Pytest suite for the core/ engines
│
└── dist/                         # PyInstaller build output (generated, not version-controlled)
```

### Notes on the Structure
- **`core/` has zero PyQt5 imports.** Every analysis engine can be unit-tested (`tests/test_core.py`)
  without launching the GUI at all — this is what keeps FR-based traceability testable in isolation.
- **`gui/` never touches SQLite directly.** GUI panels call into `core/` and `database/db_manager.py`;
  they don't run raw SQL themselves. This mirrors the separation-of-concerns rule from
  `code_hygiene_guide.md`.
- **`rules/engineering_rules.json`** is intentionally outside `core/` so a non-programmer engineer can
  find and edit it directly if needed, even without using the Settings UI.
