# AEIA Code & Folder Hygiene Guide
## A beginner's guide to understanding the project structure and writing clean code

Yes, **folder hygiene and code hygiene are present** in this project and should be actively maintained
from the very first commit. The project is structured clearly into distinct GUI, core-logic, and
database layers, with each analysis engine isolated into its own module.

This guide explains how the project is organized and sets the standard for how new code should be written.

---

## 1. Folder Structure (Folder Hygiene)

A good folder structure ensures you know exactly where to find things and where to put new things.
AEIA uses a **layered desktop-application structure** — no client-server split, everything runs in one
local Python process.

```text
AEIA/
│
├── main.py                   # Entry point — launches the PyQt5 application
├── requirements.txt          # Python dependencies, version-pinned
│
├── core/                     # Pure analysis logic — NO PyQt5 imports allowed here
│   ├── data_loader.py
│   ├── preprocessor.py
│   ├── statistics_engine.py
│   ├── anomaly_detector.py
│   ├── expert_system.py
│   ├── insight_generator.py
│   ├── recommendation_engine.py
│   ├── chart_builder.py
│   └── report_builder.py
│
├── database/                 # SQLite access — the only place raw SQL is allowed
│   ├── db_manager.py
│   ├── models.py
│   └── schema.sql
│
├── gui/                      # PyQt5 UI — the only place widgets are created
│   ├── main_window.py
│   ├── import_panel.py
│   ├── analysis_panel.py
│   ├── report_panel.py
│   ├── history_panel.py
│   ├── settings_dialog.py
│   └── theme.py              # Color Philosophy lives here, centrally
│
├── config/
│   └── settings.json
│
├── rules/
│   └── engineering_rules.json
│
└── docs/                      # Project Documentation
    ├── AEIA_requirements_context.md
    ├── color_philosophy.md
    └── code_hygiene_guide.md (This file)
```

### Why is this good hygiene?
- **Separation of Concerns**: `gui/` knows nothing about SQL, and `core/` knows nothing about PyQt5
  widgets. They communicate only through plain Python function calls and data structures (DataFrames,
  dicts, dataclasses) — never by passing widget objects around.
- **Testable Core**: Because `core/` has zero GUI dependencies, every analysis engine can be unit-tested
  headlessly (`tests/test_core.py`) without opening a single window.
- **Modular Panels**: Instead of one giant `main_window.py` with every widget, each screen
  (Import, Analysis, Report, History, Settings) is its own file in `gui/`.

---

## 2. Code Writing Format (Code Hygiene)

When writing or modifying code in this project, follow these standards to ensure it remains easy for
future developers (and yourself, six months from now) to read.

### Rule 1: Always Reference Requirements (Traceability)
Every major function must mention the Requirement ID (FR-XXX) it fulfills. This is the **most
important** rule in this project — it's how `test_cases.md` stays connected to real code.
```python
# GOOD
# FR-031: Detect outliers per numeric column using the Z-score method
def detect_zscore_outliers(series, threshold=3.0):
    ...

# BAD
def find_weird_values(s):
    ...
```

### Rule 2: DRY (Don't Repeat Yourself)
If the same logic shows up in the anomaly detector and the rule engine, extract it into a shared
utility. *Example:* severity-level classification (Info/Warning/Critical) should live in one function
in `core/anomaly_detector.py` that both `expert_system.py` and `recommendation_engine.py` import,
rather than being reimplemented in each.

### Rule 3: Naming Conventions
- **Python Variables & Functions**: `snake_case` (e.g., `compute_correlation_matrix`, `dataset_id`).
- **Python Classes**: `PascalCase` (e.g., `AnomalyResult`, `RuleDefinition`).
- **PyQt5 Widget Classes**: `PascalCase` ending in the widget type (e.g., `ImportPanel`, `SettingsDialog`).
- **Constants / Config Keys**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_ZSCORE_THRESHOLD`).

### Rule 4: Clear Variable Names
Avoid abbreviations that are difficult to understand — especially in engineering-domain code where
ambiguity can hide a real bug.
```python
# GOOD
zscore_threshold = 3.0
flagged_anomalies = []

# BAD
zt = 3.0
fa = []
```

### Rule 5: Keep Functions and Panels Small
- A Python function in `core/` should ideally do **one** thing. If a function loads a file, cleans it,
  *and* computes statistics, split it into three functions across `data_loader.py`,
  `preprocessor.py`, and `statistics_engine.py`.
- If a `gui/` panel file starts exceeding ~500 lines, pull tables, dialogs, or repeated widgets out
  into smaller sub-widgets in the same folder.

### Rule 6: No Hard-Coded Thresholds or Paths
Anomaly thresholds, rule file locations, and report folders must always be read from
`config/settings.json` or the `app_settings` table (FR-095) — never hard-coded inline. This is what
makes Settings (Module 11) actually work.

---

## 3. UI and Styling Hygiene (Color Philosophy)
- Do not write random inline colors like `setStyleSheet("color: red")` scattered through panel files.
- Use the central palette defined in `gui/theme.py`.
- When building a new panel, ensure its UI adheres strictly to the **Color Philosophy Document**
  (e.g., Critical Red only for Critical-severity findings, never for ordinary UI chrome).

---

## Conclusion
Code hygiene is like a clean lab bench. If you leave things scattered everywhere — untraced functions,
hard-coded numbers, one 2,000-line file — the next person trying to add a feature (or you, after a
two-week break) is going to struggle. By following this guide, AEIA's codebase stays clean, traceable
back to its requirements, and maintainable by a single student developer.
