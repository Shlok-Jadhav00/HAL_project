# High Level Design (HLD) - AI-Powered Engineering Insight Assistant (AEIA)

This document provides a high-level overview of the structure and flow of AEIA. It is designed to be
easily understood by a beginner.

---

## 1. System Architecture

AEIA is built as a **single-process desktop application** — there is no client-server split and no
network calls. Below is a diagram showing how the internal layers connect to each other:

```mermaid
graph TD
    subgraph Desktop ["Engineer's PC (Offline, CPU-only)"]
        GUI["PyQt5 GUI Shell (main_window.py)"]
        CORE["Core Analysis Engines (core/)"]
        RULES["Rule File (engineering_rules.json)"]
        DB[(SQLite Database - aeia.db)]
        FS["Local Filesystem (config/, reports/)"]
    end

    GUI -- "user actions (import, analyze, export)" --> CORE
    CORE -- "reads/evaluates" --> RULES
    CORE -- "reads/writes results" --> DB
    CORE -- "writes PDF/CSV reports" --> FS
    GUI -- "reads settings" --> FS
```

### Layer Responsibilities

1. **GUI Shell (PyQt5)**
   - Runs entirely on the local machine; no browser, no server.
   - Presents the Import → Preprocess → Analyze → Review → Export workflow (FR-081).
   - Runs long operations on a background thread so the interface never freezes (FR-088).

2. **Core Analysis Engines**
   - Pure Python modules with no GUI dependencies, so they can be tested independently.
   - Includes the data loader, preprocessor, statistics engine, anomaly detector, rule engine,
     insight generator, recommendation engine, and report builder.

3. **Rule File (`engineering_rules.json`)**
   - A human-editable JSON file defining the expert system's condition → conclusion rules (FR-041).
   - Loaded and validated at startup and whenever Settings changes it.

4. **Database (SQLite)**
   - A single local file (`aeia.db`) storing session history, findings, and settings.
   - No server process required — SQLite is an embedded database that lives inside the app.

5. **Filesystem**
   - Stores configuration (`settings.json`), exported reports, and the SQLite file itself.
   - The original imported dataset file is read but never copied or modified (FR-020).

---

## 2. Local Data Layout

```
%APPDATA%/AEIA/
├── config/
│   └── settings.json            # thresholds, folders, UI preferences
├── rules/
│   └── engineering_rules.json   # editable expert-system rules
├── database/
│   └── aeia.db                  # session history & results
└── reports/
    └── {SessionID}_{Timestamp}.pdf
```

There is no year/folder numbering scheme like a document-register system — each analysis **Session**
is simply identified by an auto-incrementing ID and a timestamp (FR-098). The exact report filename
convention (and every other concrete formatting detail referenced loosely in this document) is pinned
down in `implementation_specification.md` §8.

---

## 3. Core Workflow Traces

### Trace 1: Import Dataset → Preview

```mermaid
sequenceDiagram
    autonumber
    actor Eng as Engineer
    participant UI as GUI (Import Panel)
    participant Loader as core/data_loader.py
    participant DB as SQLite (aeia.db)

    Eng->>UI: Clicks "Import" and selects a CSV/XLSX/JSON/TXT/LOG file
    UI->>Loader: load_dataset(file_path)
    Loader->>Loader: Detect file type, infer column data types
    Loader-->>UI: DataFrame + column type map
    UI->>DB: Insert row into datasets (filename, path, row_count, col_count, timestamp)
    UI->>Eng: Show preview grid of first N rows
```

---

### Trace 2: Preprocess → Analyze → Detect Anomalies

```mermaid
sequenceDiagram
    autonumber
    actor Eng as Engineer
    participant UI as GUI (Analysis Panel)
    participant Prep as core/preprocessor.py
    participant Stats as core/statistics_engine.py
    participant Anom as core/anomaly_detector.py
    participant DB as SQLite (aeia.db)

    Eng->>UI: Clicks "Run Analysis"
    UI->>Prep: clean(dataframe, strategy_per_column)
    Prep-->>UI: cleaned_dataframe + preprocessing_log
    UI->>Stats: compute_statistics(cleaned_dataframe)
    Stats-->>UI: per-column stats, correlations, trends
    UI->>Anom: detect(cleaned_dataframe, methods=[zscore, iqr, isolation_forest])
    Anom-->>UI: list of anomalies with severity
    UI->>DB: Insert into sessions, statistical_results, anomalies, patterns
    UI->>Eng: Show results tab with sortable tables
```

---

### Trace 3: Evaluate Rules → Generate Insights → Conclusion

```mermaid
sequenceDiagram
    autonumber
    actor Eng as Engineer
    participant UI as GUI (Analysis Panel)
    participant Rules as core/expert_system.py
    participant NLG as core/insight_generator.py
    participant Rec as core/recommendation_engine.py
    participant DB as SQLite (aeia.db)

    UI->>Rules: evaluate(statistical_results, anomalies, rule_file)
    Rules-->>UI: list of fired rules + matched conditions
    UI->>DB: Insert into rule_matches
    UI->>NLG: generate_summary(statistics, anomalies, fired_rules)
    NLG-->>UI: plain-language Findings section
    UI->>Rec: build_recommendations(fired_rules, anomalies)
    Rec-->>UI: ranked recommendations (Critical -> Warning -> Info)
    UI->>DB: Insert into insights, recommendations
    UI->>Eng: Show Engineering Findings, Conclusion, and Recommendations for review/edit
```

---

### Trace 4: Export Report

```mermaid
sequenceDiagram
    autonumber
    actor Eng as Engineer
    participant UI as GUI (Report Panel)
    participant Builder as core/report_builder.py
    participant FS as Local Filesystem
    participant DB as SQLite (aeia.db)

    Eng->>UI: Reviews/edits notes, clicks "Export Report"
    UI->>Builder: build_pdf(session_id, include_charts=True/False)
    Builder->>Builder: Render Statistical Summary, Findings, Conclusion, Recommendations, Graphs
    Builder->>FS: Write PDF to configured reports/ folder
    UI->>DB: Insert into reports (path, timestamp, session_id)
    UI->>Eng: Show success message with file location
```

---

## 4. Why No Client-Server Diagram?

Readers familiar with networked systems (like a browser-based app talking to a remote API) may expect
a client-server diagram here. AEIA intentionally has **no server tier** — it is a single offline
executable, so "the client" and "the server" are the same process running on the engineer's own
machine (NFR-001, NFR-002, EIR-002).
