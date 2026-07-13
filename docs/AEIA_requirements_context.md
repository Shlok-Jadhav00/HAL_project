# AEIA — Project Context & Requirements
## AI-Powered Engineering Insight Assistant for Engineering Data Analysis and Decision Support

---

## Project Context

- Offline desktop application for engineers in **avionics and aerospace** domains who work with test results, sensor logs, system logs, and experimental data
- Goal: automatically analyze engineering datasets, detect meaningful patterns/anomalies, and generate explainable engineering conclusions and recommendations — replacing slow, error-prone manual analysis
- **No internet connectivity and no GPU required at any point** — the application must run fully offline on CPU-only hardware
- Single-user, single-machine desktop tool (no client-server split, no LAN dependency) — everything runs locally on the engineer's PC
- Uses **Explainable AI (XAI)**: statistical intelligence, pattern recognition, a rule-based expert system, and anomaly detection — deliberately **not** a cloud-based large language model, so every conclusion can be traced back to a number, a rule, or a detection method
- Tech Stack: **Python** · **PyQt5** (GUI; Tkinter fallback reserved if Windows 7 support becomes mandatory) · **Pandas / NumPy / SciPy** (data + stats) · **Scikit-learn** (lightweight ML) · **SQLite** (local database) · **Matplotlib** (optional charts) · **ReportLab** (PDF reports) · **NLTK / spaCy** (template-based NL summaries) · **PyInstaller** (packaging)
- Source document: `AI-Powered_Engineering_Insight_Assistant_Project_Proposal.docx` (Problem Statement → Future Scope, sections 1–13)

---

## Terminology Reference
> ⚠️ Canonical terms used throughout this document and the rest of the `docs/` set. Keep naming consistent across code, UI labels, and documentation.

| Term | Meaning |
|---|---|
| **Dataset** | A single imported file (CSV/XLSX/JSON/TXT/LOG) once loaded into the application |
| **Session** | One complete run of Import → Preprocess → Analyze → Review → Export against a Dataset |
| **Finding** | Any individual statistical fact, anomaly, or pattern surfaced by the analysis engines |
| **Anomaly** | A data point or set of points flagged as statistically or rule-wise abnormal |
| **Rule** | A single condition → conclusion/recommendation entry in the expert system's rule file |
| **Insight** | A plain-language sentence generated from one or more Findings |
| **Conclusion** | The session-level synthesis of all Findings into an overall engineering statement |
| **Recommendation** | A suggested next action tied to a specific Finding or Rule |
| **History** | The local, persisted record of past Sessions and their results |

---

## Local Storage Structure

Unlike a networked system, AEIA stores everything on the local machine, under a single configurable application data folder (default: `%APPDATA%/AEIA/` on Windows).

```
AEIA/
├── config/
│   └── settings.json            # thresholds, default folders, UI preferences (FR-095)
├── rules/
│   └── engineering_rules.json   # editable expert-system rule file (FR-041)
├── database/
│   └── aeia.db                  # SQLite database — sessions, findings, history (no raw datasets stored)
└── reports/
    └── {SessionID}_{Timestamp}.pdf   # exported reports (default location; user-configurable, FR-093)
```

**Key rule:** the *original imported dataset file is never modified or copied* into AEIA's storage — only metadata and computed results are persisted (FR-020, FR-103). This keeps the footprint small and avoids duplicating potentially sensitive engineering data.

---

## Database Schema (Summary)

All thresholds, rules, and session data are stored in SQLite — never hard-coded — so the application can be reconfigured without a code change.

| Table | Purpose |
|---|---|
| `datasets` | Metadata about each imported dataset (filename, path, row/column counts, import timestamp) |
| `sessions` | One row per analysis run; links a dataset to its results and timestamps |
| `statistical_results` | Per-column statistical output (mean, median, std dev, min/max, quartiles, etc.) for a session |
| `anomalies` | Individual detected anomalies: row reference, column(s), method, severity |
| `patterns` | Detected trends/correlations for a session |
| `rule_matches` | Which expert-system rules fired for a session, and what triggered them |
| `insights` | Generated natural-language sentences, linked back to the finding/rule that produced them |
| `recommendations` | Recommended actions, ranked by severity, linked to their source finding/rule |
| `reports` | Metadata about exported PDF reports (path, generation timestamp, session link) |
| `rule_definitions` | Cached/loaded copy of the editable rule file, for fast querying inside the app |
| `app_settings` | Key-value store mirroring `settings.json` for quick lookups from the GUI |

> ℹ️ No user-accounts table is required — see **Access Model** below.

Full `CREATE TABLE` statements are in `technical_design.md`.

---

## Functional Requirements

> 📌 **Before implementing any FR below:** the requirements here define *what* must happen, not the
> exact default values, algorithm parameters, message text, file layouts, or templates needed to build
> it — those are pinned down precisely in `implementation_specification.md`, so nothing needs to be
> guessed. This applies especially to FR-006, FR-013, FR-024, FR-031–FR-041, FR-051–FR-058, FR-071–FR-090.
> A ready-to-use sample dataset with pre-computed expected results also lives in `sample_data/`.

### Module 1 — Dataset Import

| FR ID | Requirement |
|---|---|
| FR-001 | Support importing **CSV** files |
| FR-002 | Support importing **Excel (.xlsx)** files |
| FR-003 | Support importing **JSON** files |
| FR-004 | Support importing **TXT** files (delimited or plain) |
| FR-005 | Support importing **LOG** files (semi-structured; regex-based line parsing) |
| FR-006 | Auto-detect file type from extension and content; prompt the user to confirm/select format if detection is ambiguous |
| FR-007 | Display a preview grid of the first N rows immediately after import, before committing to analysis |
| FR-008 | Automatically detect each column's data type (numeric, categorical, datetime, text) |
| FR-009 | Allow the user to select which columns to include in analysis (exclude irrelevant columns) |
| FR-010 | Store dataset metadata (filename, path, row count, column count, import timestamp) as a new `datasets` record |

### Module 2 — Data Preprocessing

| FR ID | Requirement |
|---|---|
| FR-011 | Validate dataset structure (non-empty, consistent column count per row) before processing |
| FR-012 | Detect missing values per column and report the count/percentage |
| FR-013 | Provide missing-value strategies: drop rows, fill with mean/median, fill with a constant, or leave as-is (user-selectable per column) |
| FR-014 | Detect and remove exact duplicate rows; show the count of duplicates removed |
| FR-015 | Detect inconsistent formatting (mixed date formats, stray whitespace, mixed-case categorical labels) and offer to normalize |
| FR-016 | Run a quick outlier pre-scan on numeric columns and warn the user before full analysis |
| FR-017 | Allow a basic sanity-range check per numeric column (e.g. flag implausible values if a configured range exists) |
| FR-018 | Log every preprocessing action taken (what was cleaned, how many rows/values affected) for the final report |
| FR-019 | Allow the user to undo preprocessing and revert to the raw imported dataset within the same session |
| FR-020 | Persist the cleaned dataset only in memory/session — the raw file on disk is never modified |

### Module 3 — Statistical Analysis Engine

| FR ID | Requirement |
|---|---|
| FR-021 | Compute mean, median, mode, standard deviation, and variance for every numeric column |
| FR-022 | Compute min, max, and range for every numeric column |
| FR-023 | Compute quartiles (Q1, Q3) and interquartile range (IQR) for every numeric column |
| FR-024 | Perform trend analysis (e.g. moving average, slope of linear fit) on time/sequence-ordered numeric columns |
| FR-025 | Perform pairwise Pearson correlation analysis between all numeric columns |
| FR-026 | Highlight correlations above a configurable threshold (default `\|r\| > 0.7`) as candidate relationships |
| FR-027 | Compute frequency distributions for categorical columns |
| FR-028 | Support grouped/segmented statistics (e.g. per test-run or per sensor ID) |
| FR-029 | Complete statistical computation for a 100,000-row dataset within 10 seconds on the minimum specified hardware |
| FR-030 | Present statistical results in a dedicated, sortable results tab |

### Module 4 — Pattern & Anomaly Detection

| FR ID | Requirement |
|---|---|
| FR-031 | Detect outliers per numeric column using a **Z-score** method (default threshold `\|z\| > 3`, configurable) |
| FR-032 | Detect outliers per numeric column using the **IQR** method (default `1.5×IQR`, configurable) |
| FR-033 | Detect multivariate anomalies using an **Isolation Forest** model (scikit-learn) across selected numeric columns |
| FR-034 | Allow the user to choose which detection method(s) to run per session |
| FR-035 | List every detected anomaly with its row reference, column(s), and detection method |
| FR-036 | Detect simple recurring patterns (cyclical behaviour, step changes, sustained drift) in ordered numeric columns |
| FR-037 | Detect threshold breaches against user-defined or rule-file engineering limits (e.g. "temperature > 120°C") |
| FR-038 | Assign a severity level (**Info / Warning / Critical**) to each finding based on configurable rules |
| FR-039 | Allow the user to mark an anomaly as a false positive, excluding it from the session's conclusions |
| FR-040 | All detection shall run entirely on CPU with no GPU dependency |

### Module 5 — Rule-Based Expert System

| FR ID | Requirement |
|---|---|
| FR-041 | Maintain a human-editable rule file (`engineering_rules.json`) of the form: condition → conclusion/recommendation |
| FR-042 | Support rule conditions referencing statistical results, anomaly counts, or threshold breaches |
| FR-043 | Evaluate all applicable rules against the current session's results once detection completes |
| FR-044 | Rules evaluate **independently** against session data — rule chaining is an explicit out-of-scope limitation for v1 |
| FR-045 | Allow engineers to add, edit, or disable rules via the Settings module without touching source code |
| FR-046 | Log every rule that fired, including which condition triggered it |
| FR-047 | Ship a default starter rule set (e.g. sustained upward drift, repeated threshold breach, high-variance instability) |
| FR-048 | Validate rule file syntax on load; report a clear error without crashing if malformed |
| FR-049 | Allow rules to be scoped to specific column-name patterns or applied dataset-wide |
| FR-050 | Rule evaluation shall complete within 2 seconds for a standard rule set (up to 100 rules) |

### Module 6 — Insight & Natural Language Summary Generation

| FR ID | Requirement |
|---|---|
| FR-051 | Generate a plain-language summary of the overall dataset (row/column counts, key statistics) |
| FR-052 | Generate a plain-language description for each detected anomaly, in engineering terms |
| FR-053 | Generate a plain-language description for each fired expert-system rule |
| FR-054 | Group individual findings into a structured "Engineering Findings" section by column/subsystem |
| FR-055 | Use **template-based** NLG (NLTK/spaCy-assisted phrasing), never a generative LLM — keeps the system explainable and offline |
| FR-056 | Avoid duplicate/contradictory statements when multiple findings reference the same column |
| FR-057 | Allow the user to regenerate the summary after excluding false positives (FR-039) |
| FR-058 | Summaries shall be generated without any internet connection or external API call |

### Module 7 — Conclusion & Recommendation Engine

| FR ID | Requirement |
|---|---|
| FR-059 | Generate an overall "Engineering Conclusion" synthesizing all findings for the session |
| FR-060 | Generate one or more Recommendations tied to specific findings (e.g. "Investigate sensor calibration for Channel 3") |
| FR-061 | Rank findings/recommendations by severity (Critical → Warning → Info) |
| FR-062 | Allow the user to add free-text notes/annotations to any finding or the overall conclusion before export |
| FR-063 | Recommendations shall reference the rule or detection method that produced them, for traceability |
| FR-064 | If no anomalies or rule matches exist, generate a clear "No significant findings" conclusion rather than an empty section |
| FR-065 | Conclusions/recommendations shall be reviewable and editable by the user before export — AI output is advisory, not final |

### Module 8 — Visualization (Optional)

| FR ID | Requirement |
|---|---|
| FR-066 | Generate a line/trend chart for ordered numeric columns, with anomalies highlighted |
| FR-067 | Generate a histogram/distribution chart for any selected numeric column |
| FR-068 | Generate a correlation heatmap for numeric columns |
| FR-069 | Allow charts to be toggled on/off per report (some engineers may prefer text-only) |
| FR-070 | All charts generated locally via Matplotlib — no external charting service |

### Module 9 — Report Generation

| FR ID | Requirement |
|---|---|
| FR-071 | Export a PDF report containing: Statistical Summary, Engineering Findings, Conclusion, Recommendations, and optional Graphs |
| FR-072 | Include a report header with dataset name, analysis timestamp, and software version |
| FR-073 | Include a table of contents for reports exceeding 3 sections |
| FR-074 | Allow the user to preview the report on-screen before exporting to PDF |
| FR-075 | Allow the user to choose a save location and filename for the exported PDF |
| FR-076 | Support re-exporting after editing notes/annotations (FR-062) without re-running analysis |
| FR-077 | Generate reports with ReportLab — no internet-based rendering dependency |
| FR-078 | Report generation shall complete within 15 seconds for a standard session on minimum hardware |
| FR-079 | Include a disclaimer footer noting conclusions are AI-assisted and require engineering sign-off |
| FR-080 | Support exporting raw statistical results additionally as CSV |

### Module 10 — Main Dashboard / GUI Shell

| FR ID | Requirement |
|---|---|
| FR-081 | Provide a clear workflow: **Import → Preprocess → Analyze → Review Findings → Export Report** |
| FR-082 | Provide a persistent sidebar/menu for Import, Analysis, History, and Settings views |
| FR-083 | Display a progress indicator during long-running operations |
| FR-084 | Display clear, non-technical error messages for common failures (corrupt file, unsupported format, empty dataset) |
| FR-085 | Support multiple open datasets across separate tabbed sessions within one application run |
| FR-086 | Provide a status bar showing current dataset name, row count, and last analysis timestamp |
| FR-087 | Provide keyboard shortcuts for common actions (Import: `Ctrl+O`, Export Report: `Ctrl+E`) |
| FR-088 | GUI shall remain responsive during long-running analysis (background threading; no UI freeze) |
| FR-089 | Provide an About/Help panel describing the application, version, and basic usage |
| FR-090 | GUI shall be built with **PyQt5**; a Tkinter fallback is reserved if Windows 7 support becomes mandatory |

### Module 11 — Settings & Configuration

| FR ID | Requirement |
|---|---|
| FR-091 | Allow configuring anomaly detection thresholds (Z-score threshold, IQR multiplier) |
| FR-092 | Allow viewing, adding, editing, and disabling expert-system rules from the Settings panel (FR-045) |
| FR-093 | Allow configuring the default report save folder |
| FR-094 | Allow configuring the correlation-highlight threshold (FR-026) |
| FR-095 | Store all configuration in `settings.json` — never hard-coded |
| FR-096 | Provide a "Restore Defaults" action resetting all settings to factory values |
| FR-097 | Validate all settings input (e.g. thresholds must be positive numbers) before saving |

### Module 12 — Analysis History / Session Log

| FR ID | Requirement |
|---|---|
| FR-098 | Persist a record of every completed session (dataset name, timestamp, findings count) in SQLite |
| FR-099 | Provide a History view listing past sessions, sortable by date |
| FR-100 | Allow re-opening a past session's findings and report without re-running analysis |
| FR-101 | Allow re-exporting a past session's report |
| FR-102 | Allow deleting a past session record (with confirmation) along with its stored report reference |
| FR-103 | History shall **not** store copies of original dataset files — metadata and computed results only |
| FR-104 | History records shall persist across application restarts |
| FR-105 | Support at least 500 historical session records without a noticeable slowdown in the History view |

---

## Non-Functional Requirements

| NFR ID | Category | Requirement |
|---|---|---|
| NFR-001 | Offline Operability | The system shall run with zero internet connectivity at all times; no network calls of any kind |
| NFR-002 | Hardware | Shall run on CPU-only hardware meeting the minimum spec (Intel i3, 4 GB RAM); no GPU required |
| NFR-003 | Performance | Timing budgets per FR-029 (statistics), FR-050 (rules), FR-078 (report export) |
| NFR-004 | Portability | Windows 10/11 (64-bit) primary target; packaged as a single executable |
| NFR-005 | Maintainability | Code organized into clearly separated modules (`core/`, `gui/`, `database/`); heavily commented for a single-developer/student context |
| NFR-006 | Explainability | Every AI-derived finding must trace back to a specific statistic, detection method, or rule — no "black box" outputs (Explainable AI) |
| NFR-007 | Data Privacy | Engineering datasets may be sensitive; the application shall never transmit data anywhere; the local database resides only on the user's machine |
| NFR-008 | Reliability | The application shall not crash on malformed input; all parsing wrapped in error handling with user-facing messages |
| NFR-009 | Usability | A first-time engineer (not a data scientist) shall be able to import a dataset and generate a report without reading a manual |
| NFR-010 | Extensibility | New file formats and new expert-system rules shall be addable without major refactors |
| NFR-011 | Packaging | Final deliverable is a single PyInstaller-built `.exe` requiring no separate Python install on the target machine |
| NFR-012 | Dependency Pinning | All Python dependencies version-pinned in `requirements.txt` for reproducible builds |

---

## External Interface Requirements

| EIR ID | Requirement |
|---|---|
| EIR-001 | The application shall accept CSV, XLSX, JSON, TXT, and LOG files via file-browse or drag-and-drop; no external API integrations |
| EIR-002 | The application shall not require an internet connection at any point, including for installation of the packaged executable |
| EIR-003 | The application shall run as a native Windows desktop application — no browser required |
| EIR-004 | Exported reports shall be standard PDF files, openable in any PDF reader |
| EIR-005 | The application shall interface with the local filesystem only, for reading datasets and writing reports/config/database — no external services |

---

## Access Model

AEIA is a **single-user, single-machine** desktop application. There is no login, no roles, and no RBAC matrix in the initial version — this mirrors the project proposal, which does not describe multi-user accounts. If the tool is later deployed on a shared engineering workstation, basic user separation would be a future-scope addition (see **FS-006** below).

---

## Open Items / Future Scope

| ID | Item | Notes |
|---|---|---|
| FS-001 | Support image datasets | Per proposal Future Scope |
| FS-002 | Support PDF engineering documents as input | Per proposal Future Scope |
| FS-003 | Optional integration of a lightweight local LLM for richer narrative generation | Explicitly deferred — keeps NFR-006 (Explainability) intact for the current scope |
| FS-004 | Historical analytics dashboard (trends across sessions/datasets over time) | Per proposal Future Scope; builds on Module 12 |
| FS-005 | Engineering knowledge base (browsable, expanded rule/knowledge library) | Per proposal Future Scope |
| FS-006 | Multi-user / login support | Only if deployed on a shared workstation |
| FS-007 | Windows 7 / Tkinter fallback UI | Only if Windows 7 support becomes mandatory (per proposal Tech Stack note) |

---

*Document Version: 1.0 | Status: Requirements drafted from Project Proposal — ready for design phase*
