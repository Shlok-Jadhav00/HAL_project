# AEIA — Complete Project Technical Documentation

**AI-Powered Engineering Insight Assistant**
A fully offline, CPU-only desktop application for avionics and aerospace engineers.

---

## Table of Contents

1. [What is AEIA?](#1-what-is-aeia)
2. [Architecture Overview](#2-architecture-overview)
3. [The Explainable AI (XAI) Philosophy](#3-the-explainable-ai-xai-philosophy)
4. [Complete Data Flow — From CSV to PDF Report](#4-complete-data-flow--from-csv-to-pdf-report)
5. [Module-by-Module Deep Dive](#5-module-by-module-deep-dive)
6. [The Database Layer](#6-the-database-layer)
7. [The GUI Layer](#7-the-gui-layer)
8. [The Rule Engine — How Engineers Customize AEIA](#8-the-rule-engine--how-engineers-customize-aeia)
9. [Performance Optimization Techniques](#9-performance-optimization-techniques)
10. [Deployment & Packaging](#10-deployment--packaging)
11. [File & Folder Structure](#11-file--folder-structure)
12. [Key Algorithms & Formulas](#12-key-algorithms--formulas)

---

## 1. What is AEIA?

AEIA is a **single-user desktop application** that takes engineering datasets (CSV, XLSX, JSON, TXT, LOG files), runs statistical analysis and anomaly detection on them, applies domain-specific engineering rules, and produces a **professional PDF report** with plain-language findings and recommendations.

It is designed for **HAL (Hindustan Aeronautics Limited)** engineering workstations that are:
- **Fully offline** — no internet connection, ever
- **CPU-only** — no dedicated GPU
- **Air-gapped** — no network calls, no cloud services
- **Single-user** — one engineer, one machine

The entire application runs as a single process with an embedded SQLite database. There is no server, no Docker, no browser — just one `.exe` file that the engineer double-clicks.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AEIA Application                         │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │   gui/       │   │   core/      │   │   database/      │    │
│  │              │   │              │   │                  │    │
│  │ main_window  │──▶│ data_loader  │   │ db_manager.py    │    │
│  │ import_panel │   │ preprocessor │◀─▶│ models.py        │    │
│  │ analysis_    │   │ statistics_  │   │ schema.sql       │    │
│  │   panel      │   │   engine     │   │                  │    │
│  │ report_panel │   │ anomaly_     │   │ (SQLite — 11     │    │
│  │ history_     │   │   detector   │   │  tables, zero    │    │
│  │   panel      │   │ expert_system│   │  server needed)  │    │
│  │ settings_    │   │ insight_     │   │                  │    │
│  │   dialog     │   │   generator  │   └──────────────────┘    │
│  │ theme.py     │   │ recommend-   │                           │
│  │ models.py    │   │   ation_     │   ┌──────────────────┐    │
│  │              │   │   engine     │   │   config/        │    │
│  └──────────────┘   │ executive_   │   │ settings.json    │    │
│                     │   summary_   │   │                  │    │
│   PyQt5 only ▲      │   composer   │   │   rules/         │    │
│   No raw SQL  │      │ chart_builder│   │ engineering_     │    │
│               │      │ report_     │   │   rules.json     │    │
│               │      │   builder   │   └──────────────────┘    │
│               │      │ config_     │                           │
│               │      │   manager   │   Zero PyQt5 imports ▲   │
│               │      └──────────────┘   Zero network calls │   │
│               │                         Zero GPU dependency│   │
└───────────────┴─────────────────────────────────────────────┘
```

### The Three Strict Separation Rules

| Rule | Enforcement |
|:-----|:------------|
| `core/` must have **zero PyQt5 imports** | Logic is completely independent of the GUI |
| `database/` must have **zero PyQt5 imports** | Data access is independent of the GUI |
| `gui/` must have **zero raw SQL** | All DB access goes through `database/db_manager.py` |

This means if HAL ever needs to swap the GUI framework (e.g., from PyQt5 to Tkinter for Windows 7 compatibility), every single `core/` and `database/` module works unchanged.

---

## 3. The Explainable AI (XAI) Philosophy

This is the single most important design decision in AEIA. **There is no generative LLM anywhere in the application.**

### Why Not Use ChatGPT / LLaMA / etc.?

1. **Explainability**: When AEIA says "Engine temperature exceeded the critical safety threshold of 120°C", an engineer must be able to trace that exact sentence back to a specific rule (`RULE-001`), a specific data point (row 45, column `Engine_Temp`), and a specific threshold (120°C from `engineering_rules.json`). A generative LLM cannot guarantee this traceability.

2. **Determinism**: If you run AEIA on the same dataset twice, you get the *exact same* findings, word-for-word. Generative models produce different text each time.

3. **Offline Requirement**: Running a local LLM would require a GPU and gigabytes of model weights. AEIA must run on standard office PCs with no GPU.

### How AEIA Achieves "AI" Without an LLM

AEIA uses three deterministic AI/ML techniques:

| Technique | What It Does | Where in Code |
|:----------|:-------------|:-------------|
| **Statistical Analysis** | Mean, median, std dev, trend analysis, correlation matrices | `core/statistics_engine.py` |
| **Anomaly Detection** (Z-Score, IQR, Isolation Forest) | Finds unusual data points using mathematical thresholds | `core/anomaly_detector.py` |
| **Rule-Based Expert System** | Applies human-authored engineering rules to the statistics | `core/expert_system.py` |

The "natural language" output is generated using **template-based NLG (Natural Language Generation)** — pre-written sentence templates with placeholder slots that get filled with actual computed values:

```python
# Example template from core/insight_generator.py
"Column '{column}' shows an unusual value of {value} at row {row}, 
 which is {z_score} standard deviations from the mean — 
 flagged as a statistical outlier ({severity})."
```

The **Executive Summary Composer** (`core/executive_summary_composer.py`) takes this further with a 4-stage deterministic NLP pipeline:
1. **Stage 1**: Classify and group findings into narrative categories
2. **Stage 2**: Select paragraph-level engineering narrative templates
3. **Stage 3**: spaCy-assisted linguistic post-processing (grammar smoothing, abbreviation expansion like `Temp` → `temperature`)
4. **Stage 4**: Assemble the final summary with traceability metadata back to the original findings

Every single sentence in the output traces back to a specific Finding object. There is zero hallucination, zero randomness.

---

## 4. Complete Data Flow — From CSV to PDF Report

```
┌─────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  Import  │────▶│ Preprocess   │────▶│  Statistical   │────▶│   Anomaly    │
│  CSV/    │     │              │     │  Analysis      │     │  Detection   │
│  XLSX/   │     │ • Validate   │     │               │     │              │
│  JSON/   │     │ • Clean NaN  │     │ • Mean/Median │     │ • Z-Score    │
│  TXT/    │     │ • Remove     │     │ • Std Dev     │     │ • IQR        │
│  LOG     │     │   duplicates │     │ • Trend/Slope │     │ • Isolation  │
│          │     │ • Normalize  │     │ • Correlation │     │   Forest     │
└─────────┘     └──────────────┘     └───────────────┘     └──────────────┘
                                            │                      │
                                            ▼                      ▼
                                     ┌──────────────┐     ┌──────────────┐
                                     │  Expert      │◀────│  Rule        │
                                     │  System      │     │  Matching    │
                                     │              │     │  (JSON)      │
                                     │ IF stat X >  │     │              │
                                     │ threshold Y  │     │ 6 default    │
                                     │ THEN fire    │     │ engineering  │
                                     │ conclusion Z │     │ rules        │
                                     └──────┬───────┘     └──────────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │  Insight     │
                                     │  Generator   │
                                     │              │
                                     │ Template NLG │
                                     │ Group by col │
                                     │ Deduplicate  │
                                     └──────┬───────┘
                                            │
                                ┌───────────┴───────────┐
                                ▼                       ▼
                         ┌──────────────┐       ┌──────────────┐
                         │  Conclusion  │       │  Chart       │
                         │  & Recommend │       │  Builder     │
                         │  Engine      │       │ (on-demand)  │
                         │              │       │              │
                         │ Executive    │       │ • Trend      │
                         │ Summary +    │       │ • Histogram  │
                         │ Ranked Recs  │       │ • Heatmap    │
                         └──────┬───────┘       └──────┬───────┘
                                │                      │
                                ▼                      ▼
                         ┌─────────────────────────────────────┐
                         │          Report Builder             │
                         │                                     │
                         │  PDF (ReportLab) with:              │
                         │  • Executive Summary                │
                         │  • Statistics Table                 │
                         │  • Anomaly List                     │
                         │  • Engineering Findings             │
                         │  • Charts (if included)             │
                         │  • Recommendations                  │
                         │  • Disclaimer                       │
                         │                                     │
                         │  CSV (flat export of stats/anomaly) │
                         └─────────────────────────────────────┘
```

---

## 5. Module-by-Module Deep Dive

### Module 1: Dataset Import (`core/data_loader.py`)

**What it does**: Imports CSV, XLSX, JSON, TXT, and LOG files into a pandas DataFrame.

**Key techniques**:
- **Automatic file type detection**: Uses file extension mapping (`.csv` → CSV, `.xlsx` → XLSX, etc.)
- **Delimiter sniffing**: For CSV/TXT files, uses Python's `csv.Sniffer` to automatically detect whether the file uses commas, tabs, semicolons, or pipes as delimiters — with a defined fallback order
- **Column type inference**: Automatically classifies each column as `numeric`, `categorical`, `datetime`, or `text` using pandas dtype detection
- **LOG file parsing**: Uses a regex pattern to extract `timestamp`, `level`, and `message` from standard log format
- **Ragged-row detection**: Validates that every row has the same number of columns as the header

**FRs**: FR-001 through FR-010

---

### Module 2: Data Preprocessing (`core/preprocessor.py`)

**What it does**: Cleans and validates the raw dataset before analysis.

**Key techniques**:
- **Missing value detection**: Reports count and percentage of NaN values per column
- **Missing value imputation strategies**: 5 strategies — `drop` rows, `fill_mean`, `fill_median`, `fill_constant`, or `leave` as-is
- **Duplicate detection and removal**: Uses pandas `duplicated()` to find and optionally remove exact duplicate rows
- **Data type coercion**: Attempts to convert string columns that contain numeric values to proper numeric types
- **Structure validation**: Rejects empty datasets and datasets with inconsistent column counts

**FRs**: FR-011 through FR-020

---

### Module 3: Statistical Analysis Engine (`core/statistics_engine.py`)

**What it does**: Computes comprehensive descriptive statistics for every numeric column.

**Key computations per column**:
| Statistic | Formula/Method |
|:----------|:---------------|
| Mean | `numpy.mean()` |
| Median | `numpy.median()` |
| Mode | `scipy.stats.mode()` |
| Standard Deviation | `numpy.std(ddof=1)` — sample std dev |
| Variance | `numpy.var(ddof=1)` |
| Min / Max | `numpy.min()` / `numpy.max()` |
| Q1 / Q3 | `numpy.percentile(25)` / `numpy.percentile(75)` |
| IQR | `Q3 - Q1` |
| Coefficient of Variation | `std_dev / mean` |
| Trend Slope | `numpy.polyfit(degree=1)` — linear regression |
| Moving Average | `pandas.Series.rolling(window=w, center=True).mean()` |

**Correlation analysis**:
- Computes a full Pearson correlation matrix across all numeric columns
- Flags any pair with `|r| > 0.7` (configurable) as a "strong correlation"

**Trend direction classification**:
- `Increasing`: slope > minimum_slope_magnitude
- `Decreasing`: slope < -minimum_slope_magnitude  
- `Stable`: slope within ±minimum_slope_magnitude

All threshold parameters are read from `config/settings.json` — nothing is hardcoded.

**FRs**: FR-021 through FR-030

---

### Module 4: Pattern & Anomaly Detection (`core/anomaly_detector.py`)

**What it does**: Identifies outliers and unusual data points using three independent methods.

#### Method 1: Z-Score Detection
- **How it works**: For each value in a numeric column, compute how many standard deviations it is from the mean: `z = (x - mean) / std_dev`
- **Threshold**: Default 3.0 (from `settings.json`). Values with `|z| > 3.0` are flagged.
- **When it's best**: Works well when data is approximately normally distributed.

#### Method 2: IQR (Interquartile Range) Detection
- **How it works**: Compute `Q1`, `Q3`, and `IQR = Q3 - Q1`. Flag values below `Q1 - 1.5×IQR` or above `Q3 + 1.5×IQR`.
- **Threshold**: Default multiplier 1.5 (from `settings.json`).
- **When it's best**: Robust against skewed distributions where Z-Score might miss outliers.

#### Method 3: Isolation Forest (Multivariate)
- **How it works**: A scikit-learn machine learning algorithm that builds random decision trees to "isolate" each data point. Points that are easy to isolate (require fewer splits) are anomalies because they are different from the bulk of the data.
- **Key parameters** (all from `settings.json`):
  - `contamination = 0.05` (expect ~5% of data to be anomalous)
  - `n_estimators = 50` (number of trees)
  - `n_jobs = 1` (single-threaded for CPU safety)
  - `random_state = 42` (deterministic results)
- **When it's best**: Catches complex anomalies that span multiple columns simultaneously (e.g., "RPM is normal, temperature is normal, but RPM + temperature together is unusual")

**FRs**: FR-031 through FR-040

---

### Module 5: Rule-Based Expert System (`core/expert_system.py`)

**What it does**: Evaluates a set of human-authored engineering rules against the computed statistics and anomalies.

**How a rule works** (from `rules/engineering_rules.json`):
```json
{
  "rule_id": "RULE-001",
  "rule_name": "Critical Threshold Breach - Engine Temperature",
  "is_enabled": true,
  "scope_pattern": "Engine_Temp*",
  "condition": {
    "metric": "raw_value",
    "operator": ">",
    "value": 120
  },
  "conclusion_text": "Engine temperature exceeded the critical safety threshold of 120°C.",
  "recommendation_text": "Immediately inspect the cooling system...",
  "severity": "Critical"
}
```

**Evaluation logic**:
1. For each enabled rule, check which columns match its `scope_pattern` (uses `fnmatch` glob matching — e.g., `Engine_Temp*` matches `Engine_Temp_C`, `Engine_Temp_Sensor_2`)
2. For each matching column, extract the `metric` value (e.g., `mean`, `std_dev`, `trend_slope`, `anomaly_count`)
3. Compare using the `operator` (e.g., `>`, `>=`, `<`, `==`)
4. If the condition is true, the rule "fires" and its `conclusion_text` and `recommendation_text` become part of the findings

**Default rules include**:
- RULE-001: Critical temperature threshold breach
- RULE-002: Sustained upward drift detection
- RULE-003: High variance instability
- RULE-004: Repeated threshold breaches
- RULE-005: Strong correlation alert
- RULE-006: Isolation Forest multivariate flag

Engineers can add, modify, or disable rules by editing the JSON file — no code changes required.

**FRs**: FR-041 through FR-050

---

### Module 6: Insight & NL Summary Generation (`core/insight_generator.py` + `core/executive_summary_composer.py`)

**What it does**: Converts raw numerical findings into plain-language sentences that engineers can read and understand.

**Template-based NLG**: Every insight is generated by filling a pre-authored template:
```
Input:  column="Engine_RPM", value=9850.5, row=45, z_score=3.42, severity="Warning"
Template: "Column '{column}' shows an unusual value of {value} at row {row}, 
           which is {z_score} standard deviations from the mean..."
Output: "Column 'Engine_RPM' shows an unusual value of 9850.5 at row 45, 
         which is 3.42 standard deviations from the mean — 
         flagged as a statistical outlier (Warning)."
```

**Deduplication** (FR-056): If both Z-Score and IQR flag the same data point, only one insight is generated (to avoid noise).

**Grouping** (FR-054): Findings are grouped by column name so the engineer can focus on one sensor/measurement at a time.

**Executive Summary Composer**: A 4-stage pipeline that assembles all individual insights into a cohesive engineering narrative:
- Humanizes column names (`Engine_Temp_C` → `engine temperature`)
- Groups by narrative category (anomalies, trends, correlations, rule matches)
- Selects paragraph templates based on severity distribution
- Assembles with proper engineering transitions and a professional tone

**FRs**: FR-051 through FR-058

---

### Module 7: Conclusion & Recommendation Engine (`core/recommendation_engine.py`)

**What it does**: Synthesizes all findings into a single engineering conclusion and produces ranked, actionable recommendations.

**Conclusion generation**: Calls the Executive Summary Composer to produce a professional-grade overall assessment. If no findings exist, it generates: *"No significant anomalies, threshold breaches, or rule matches were found in this dataset."*

**Recommendation ranking** (FR-061): Sorted by severity — Critical first, then Warning, then Info.

**FRs**: FR-059 through FR-065

---

### Module 8: Visualization (`core/chart_builder.py`)

**What it does**: Generates publication-quality Matplotlib charts.

**Chart types**:
| Chart | Purpose |
|:------|:--------|
| **Trend Chart** | Line plot of each numeric column with anomaly markers (red dots), moving average overlay (dashed), and linear trend line |
| **Histogram** | Distribution of each numeric column with mean (red dashed) and median (green dash-dot) lines |
| **Correlation Heatmap** | Color-coded matrix showing Pearson r values between all numeric column pairs |

**Key design decisions**:
- Uses `matplotlib.use('Agg')` — a non-interactive backend that requires no display server. This is critical for both the `.exe` (which has no console) and for generating charts in a background thread.
- All chart colors come from `color_philosophy.md` — Signal Blue for data lines, Alert Red for anomalies, Confirmed Green for medians.
- Charts are rendered to PNG bytes in memory (`io.BytesIO`) — never saved to temporary files on disk.

**On-demand generation**: Charts are NOT generated during the main analysis pipeline (to keep it fast). They are only rendered when:
1. The user clicks "Generate Charts" in the Graphs tab, OR
2. The user exports a PDF with "Include charts" checked

Once generated, they are cached in session memory so they don't get regenerated.

**FRs**: FR-066 through FR-070

---

### Module 9: Report Generation (`core/report_builder.py`)

**What it does**: Exports a professional PDF report and/or a flat CSV file.

**PDF structure** (via ReportLab):
1. Title page with AEIA branding
2. Executive Summary (the composed engineering conclusion)
3. Statistics table (all per-column stats)
4. Anomaly list with severity badges
5. Engineering Findings grouped by column
6. Charts (if included) — trend, histogram, heatmap
7. Recommendations (ranked by severity)
8. Disclaimer: *"Findings and recommendations are advisory and require review and sign-off by a qualified engineer before any operational decision is made."*

**CSV export**: A flat tabular export of statistics and anomalies for further analysis in Excel.

**FRs**: FR-071 through FR-080

---

### Module 10: GUI Shell (`gui/main_window.py` + panels)

**What it does**: The PyQt5 desktop interface with a sidebar navigation and tabbed content panels.

**Layout**:
- **Sidebar** (left): Navigation buttons for Import, Analysis, History, Settings, About
- **Content area** (right): Swappable panels using `QStackedWidget`
- **Menu bar**: File menu with Import, Export, and Exit shortcuts

**FRs**: FR-081 through FR-090

---

### Module 11: Settings & Configuration (`gui/settings_dialog.py`)

**What it does**: Provides a GUI dialog for engineers to adjust detection thresholds, file paths, and UI preferences without editing JSON by hand.

**FRs**: FR-091 through FR-097

---

### Module 12: Session History (`gui/history_panel.py`)

**What it does**: Displays a table of past analysis sessions with dataset name, timestamp, status, and findings count. Allows re-opening or deleting old sessions.

**FRs**: FR-098 through FR-105

---

## 6. The Database Layer

AEIA uses **SQLite** — an embedded, file-based database engine. There is no separate database server to install or run.

**Schema** (`database/schema.sql`) — 11 tables:

| Table | Purpose | Key FR |
|:------|:--------|:-------|
| `datasets` | Imported file metadata (name, path, type, row/column counts) | FR-010 |
| `sessions` | Analysis session tracking (start time, status, findings count) | FR-098 |
| `statistical_results` | Per-column stats (mean, median, std_dev, trend, etc.) | FR-021–028 |
| `anomalies` | Detected outliers (column, row, method, severity, value) | FR-031–039 |
| `patterns` | Trends and correlations | FR-025–026 |
| `rule_definitions` | Cached copy of engineering rules | FR-041–049 |
| `rule_matches` | Which rules fired in which sessions | FR-043–046 |
| `insights` | Generated plain-language findings | FR-051–058 |
| `recommendations` | Ranked action items | FR-059–065 |
| `reports` | Export metadata (path, format, timestamp) | FR-071–080 |
| `app_settings` | Key-value settings mirror | FR-091–097 |

**Access pattern**: Only `database/db_manager.py` executes raw SQL. All other modules call its methods.

---

## 7. The GUI Layer

### Theme System (`gui/theme.py`)

All UI colors are centralized in `theme.py` and sourced from the AEIA Color Philosophy:

| Color | Hex | Purpose |
|:------|:----|:--------|
| Instrument Navy | `#10243E` | Sidebar background, authority |
| Signal Blue | `#2563EB` | Primary action buttons, data lines |
| Console Grey | `#F7F8FA` | Content area background |
| Panel White | `#FFFFFF` | Cards and tables |
| Steel Line | `#D3D8E0` | Borders and dividers |
| Graphite | `#111827` | Primary text |
| Muted Slate | `#6B7280` | Secondary/helper text |
| Alert Red | `#DC2626` | Critical severity |
| Caution Amber | `#D97706` | Warning severity |
| Confirmed Green | `#16A34A` | Success states, Info severity |

No GUI module ever uses inline hex codes — everything is imported from `theme.py`.

### Background Threading

Three `QThread` workers ensure the UI never freezes:
- `LoadWorker` — imports and parses the dataset file
- `AnalysisWorker` — runs the full 7-module analysis pipeline
- `ChartWorker` — generates Matplotlib charts on demand

---

## 8. The Rule Engine — How Engineers Customize AEIA

The file `rules/engineering_rules.json` is a human-editable JSON file that engineers can modify without touching any Python code.

**Adding a new rule** is as simple as adding a JSON block:
```json
{
  "rule_id": "RULE-007",
  "rule_name": "Oil Pressure Drop Alert",
  "is_enabled": true,
  "scope_pattern": "Oil_Pressure*",
  "condition": {
    "metric": "mean",
    "operator": "<",
    "value": 30
  },
  "conclusion_text": "Average oil pressure dropped below the minimum safe threshold.",
  "recommendation_text": "Check the oil pump and filter for blockages.",
  "severity": "Critical"
}
```

**Available metrics**: `raw_value`, `mean`, `std_dev`, `trend_slope`, `coefficient_of_variation`, `correlation`, `anomaly_count`, `isolation_forest_flag`

**Available operators**: `>`, `>=`, `<`, `<=`, `==`, `!=`

**Scope patterns**: Use `*` wildcards to match column names. `Engine_Temp*` matches any column starting with `Engine_Temp`. `*` alone matches every column.

---

## 9. Performance Optimization Techniques

| Technique | Implementation | Why |
|:----------|:---------------|:----|
| **Vectorized operations** | All stats use `numpy`/`pandas` C-level ops, not Python loops | 100-1000x faster than Python loops for large datasets |
| **Background threading** | `QThread` workers for import, analysis, charts | UI never freezes, even on 50,000+ row datasets |
| **Lazy chart generation** | Charts only created when user requests them | Saves 5-10 seconds per analysis on large datasets |
| **Chart caching** | Generated charts stored in session memory | No regeneration when switching tabs |
| **Settings caching** | `config_manager.py` caches `settings.json` in memory | Avoids repeated disk reads during analysis |
| **Console suppression** | `sys.frozen` check skips `StreamHandler` in `.exe` mode | Eliminates Windows terminal I/O bottleneck |
| **Single-threaded ML** | Isolation Forest `n_jobs=1` | Prevents thread contention on low-core-count CPUs |
| **Agg backend** | `matplotlib.use('Agg')` | No display server required, faster rendering |

---

## 10. Deployment & Packaging

### How the `.exe` is Built

PyInstaller bundles the entire Python interpreter, all libraries, and all data files into a single `AEIA.exe`:

```
pyinstaller --onefile --windowed --name AEIA \
    --add-data "config/settings.json;config" \
    --add-data "rules/engineering_rules.json;rules" \
    --add-data "database/schema.sql;database" \
    main.py
```

**Flags explained**:
- `--onefile`: Everything in one `.exe` (~138 MB)
- `--windowed`: No background console window
- `--add-data`: Bundles non-code files (config, rules, schema)

### First-Run Behavior

When `AEIA.exe` launches for the first time:
1. Creates `%APPDATA%/AEIA/` with subdirectories: `config/`, `rules/`, `database/`, `reports/`, `logs/`
2. Copies default `settings.json` and `engineering_rules.json` from the bundle
3. Creates the SQLite database (`aeia.db`) and initializes the 11-table schema
4. Opens the main window

### Where Data Lives

| Data | Location |
|:-----|:---------|
| Application settings | `%APPDATA%/AEIA/config/settings.json` |
| Engineering rules | `%APPDATA%/AEIA/rules/engineering_rules.json` |
| SQLite database | `%APPDATA%/AEIA/database/aeia.db` |
| Session logs | `%APPDATA%/AEIA/logs/aeia_session.log` |
| Exported reports | `Documents/AEIA_Reports/` |

---

## 11. File & Folder Structure

```
E:\AEIA\
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── AEIA.spec                        # PyInstaller build config
│
├── core/                            # Business logic (zero PyQt5)
│   ├── __init__.py                  # Version string
│   ├── config_manager.py            # Settings loader + path resolver
│   ├── color_palette.py             # Hex color constants for reports
│   ├── data_loader.py               # Module 1: Import CSV/XLSX/JSON/TXT/LOG
│   ├── preprocessor.py              # Module 2: Clean, validate, impute
│   ├── statistics_engine.py         # Module 3: Descriptive stats + correlation
│   ├── anomaly_detector.py          # Module 4: Z-Score + IQR + Isolation Forest
│   ├── expert_system.py             # Module 5: Rule engine
│   ├── insight_generator.py         # Module 6: Template NLG
│   ├── executive_summary_composer.py# Module 6b: 4-stage NLP pipeline
│   ├── recommendation_engine.py     # Module 7: Conclusion + ranked recs
│   ├── chart_builder.py             # Module 8: Matplotlib charts
│   └── report_builder.py           # Module 9: PDF + CSV export
│
├── gui/                             # PyQt5 desktop interface
│   ├── __init__.py
│   ├── theme.py                     # Color palette + global stylesheet
│   ├── models.py                    # QAbstractTableModel subclasses
│   ├── main_window.py               # Module 10: Main window + sidebar
│   ├── import_panel.py              # Dataset import UI
│   ├── analysis_panel.py            # Analysis results + Graphs tab
│   ├── report_panel.py              # PDF/CSV export UI
│   ├── history_panel.py             # Module 12: Session history
│   └── settings_dialog.py           # Module 11: Settings UI
│
├── database/                        # SQLite data layer (zero PyQt5)
│   ├── __init__.py
│   ├── schema.sql                   # 11-table DDL
│   ├── db_manager.py                # CRUD operations
│   └── models.py                    # Named tuple data models
│
├── config/
│   └── settings.json                # All tunable parameters
│
├── rules/
│   └── engineering_rules.json       # Human-editable rule definitions
│
├── sample_data/
│   └── engine_test_run.csv          # Ground-truth test dataset
│
├── docs/                            # Design documentation
├── tests/                           # Unit tests
├── dist/
│   └── AEIA.exe                     # Compiled application (~138 MB)
└── build/                           # PyInstaller temp files
```

---

## 12. Key Algorithms & Formulas

### Z-Score Outlier Detection
```
z = (x - mean) / std_dev
If |z| > threshold (default 3.0), flag as anomaly
```

### IQR Outlier Detection
```
IQR = Q3 - Q1
Lower bound = Q1 - (multiplier * IQR)    (default multiplier = 1.5)
Upper bound = Q3 + (multiplier * IQR)
If x < lower_bound OR x > upper_bound, flag as anomaly
```

### Isolation Forest
```
- Build 50 random decision trees (n_estimators=50)
- Each tree randomly selects a feature and split point
- Anomalies are isolated in fewer splits (shorter path length)
- Points with prediction == -1 are anomalies
- contamination=0.05 means ~5% of data expected to be anomalous
```

### Linear Trend Analysis
```
slope, intercept = numpy.polyfit(x, y, degree=1)
If slope >  minimum_slope_magnitude -> "Increasing"
If slope < -minimum_slope_magnitude -> "Decreasing"
Otherwise -> "Stable"
```

### Moving Average
```
MA(w) = pandas.Series.rolling(window=w, center=True).mean()
w = max(min_samples, min(max_samples, int(len(data) * fraction)))
```

### Pearson Correlation
```
r = sum((xi - x_mean)(yi - y_mean)) / sqrt(sum(xi - x_mean)^2 * sum(yi - y_mean)^2)
If |r| > correlation_threshold (default 0.7), flag as "strong"
```

### Coefficient of Variation
```
CV = std_dev / mean
Used by RULE-003 to detect instability (CV > 0.15 = Warning)
```

---

> **This document covers the complete AEIA system — from the moment a CSV file is imported to the moment a PDF report is exported. Every module, every algorithm, and every design decision is documented here for handover to the HAL engineering team.**
