# AEIA Implementation Specification
## Every concrete value, algorithm parameter, schema, and template a coding assistant needs — so nothing has to be invented

This document exists for one reason: the other `docs/` files describe **what** AEIA must do (105 FRs
across 12 modules), but on their own they leave many **exact values** unspecified — the kind of thing
a coding assistant would otherwise have to guess silently while implementing. This file closes every
one of those gaps with a specific, deterministic answer, and cross-references the FR/NFR it satisfies.

If you are implementing AEIA and need to decide a constant, a default, a message string, a layout
number, or an algorithm parameter — **check here first.** If it truly isn't here, that's the one thing
left to ask the project owner (Shlok) about; everything else below is decided.

---

## 1. Versioning Scheme

- **Scheme:** Semantic Versioning (`MAJOR.MINOR.PATCH`).
- **Starting version:** `0.1.0` during development; move to `1.0.0` once every FR in
  `AEIA_requirements_context.md` passes its corresponding test in `test_cases.md`.
- **Where it lives:** a single `__version__ = "0.1.0"` constant in `core/__init__.py`. Every other
  place that needs the version (report header FR-072, About panel FR-089, PyInstaller `.spec` file)
  imports this constant — it is never hard-coded a second time anywhere else.

---

## 2. Configuration Files (ready to use, not just described)

Three seed files are provided alongside this spec and should be copied directly into the project:

| File | Goes in | Satisfies |
|---|---|---|
| `seed_files/settings.json` | `config/settings.json` (shipped default; copied to `%APPDATA%/AEIA/config/` on first run) | FR-095, FR-096, Module 11 |
| `seed_files/engineering_rules.json` | `rules/engineering_rules.json` (default starter rule set) | FR-047, Module 5 |
| `seed_files/schema.sql` | `database/schema.sql` (extracted verbatim from `technical_design.md` — guaranteed identical) | Part A of `technical_design.md` |
| `seed_files/requirements.txt` | Project root | NFR-012 |

**Settings key reference** (all keys present in `settings.json`, all validated per FR-097 — positive numbers only where noted):

| Key | Default | Meaning | FR |
|---|---|---|---|
| `detection.zscore_threshold` | `3.0` | \|z\| above this = outlier | FR-031, FR-091 |
| `detection.iqr_multiplier` | `1.5` | multiplier on IQR for outlier bounds | FR-032, FR-091 |
| `detection.isolation_forest_contamination` | `0.05` | expected anomaly fraction | FR-033 |
| `detection.isolation_forest_n_estimators` | `100` | number of trees | FR-033 |
| `detection.isolation_forest_random_state` | `42` | fixed seed for reproducible results between runs | FR-033 |
| `statistics.correlation_threshold` | `0.7` | \|r\| above this = "strong" | FR-026, FR-094 |
| `statistics.trend_window_min_samples` / `_max_samples` / `_fraction_of_dataset` | `3` / `20` / `0.1` | see §4 Trend Analysis formula | FR-024 |
| `statistics.trend_stability_std_multiplier` | `0.5` | see §4 direction classification | FR-024, FR-036 |
| `preprocessing.default_numeric_fill_constant` | `0` | default value for "fill with a constant" on numeric columns (user-editable) | FR-013 |
| `preprocessing.default_categorical_fill_constant` | `"Unknown"` | same, for categorical/text columns | FR-013 |
| `paths.default_report_folder` | `%APPDATA%\AEIA\reports` | FR-093 |
| `ui.window_width` / `window_height` | `1440` / `900` | default window size | FR-081, §7 |
| `ui.window_min_width` / `window_min_height` | `1280` / `800` | minimum resizable window size | §7 |
| `ui.sidebar_width` / `sidebar_collapsed_width` | `220` / `60` (px) | §7 |
| `report.page_size` | `"A4"` | §8 |
| `report.margin_cm` | `2` | §8 |

**Important architectural note (resolves an easy point of confusion):** there are *two separate,
intentionally distinct* places a "threshold" can live:
- **`settings.json` → global statistical thresholds** (Z-score, IQR multiplier, correlation threshold)
  apply the *same way to every numeric column* — these are Module 3/4 concerns.
- **`engineering_rules.json` → domain-specific limits** (e.g. "Engine_Temp_C > 120") apply to
  *specific named columns* and carry engineering meaning — these are Module 5 concerns.
Do not merge these two mechanisms; FR-037's "threshold breach" is implemented as a rule (see §3), not
as a third detection method.

---

## 3. Rule File Schema (fills FR-041, FR-042, FR-048, FR-049)

Every entry in `rules` inside `engineering_rules.json` follows exactly this shape:

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
  "recommendation_text": "Immediately inspect the cooling system and sensor calibration for the affected channel.",
  "severity": "Critical"
}
```

| Field | Required | Notes |
|---|---|---|
| `rule_id` | Yes | Unique string, convention `RULE-NNN` |
| `rule_name` | Yes | Human-readable label shown in Settings (FR-045) |
| `is_enabled` | Yes | Toggle without deleting the rule (FR-045) |
| `scope_pattern` | Yes | A glob-style pattern (`fnmatch` semantics) against column names, or `"*"` for dataset-wide (FR-049) |
| `condition.metric` | Yes | One of the 7 metric types below |
| `condition.method_filter` | No | Only used with `metric: anomaly_count` — restricts the count to one detection method (`ZScore`, `IQR`, `IsolationForest`, `ThresholdBreach`) |
| `condition.operator` | Yes | One of `>`, `>=`, `<`, `<=`, `==`, `!=` |
| `condition.value` | Yes | Number or boolean, compared against the metric |
| `conclusion_text` | Yes | Fed into the NLG layer (§5) |
| `recommendation_text` | No | If omitted, no recommendation is generated for this rule, only a finding |
| `severity` | Yes | `Info`, `Warning`, or `Critical` (FR-038) |

### The 7 valid `metric` values

| Metric | Compares against | Example use |
|---|---|---|
| `raw_value` | Every individual data point in the scoped column(s) | Simple threshold breach (FR-037) |
| `mean` | The column's computed mean | "Average pressure too low" style rules |
| `std_dev` | The column's computed standard deviation | Raw-spread rules |
| `trend_slope` | The column's linear-fit slope (§4) | Drift detection (RULE-002) |
| `coefficient_of_variation` | `std_dev / mean` for the column | Relative instability (RULE-003) |
| `correlation` | The absolute Pearson `r` between the scoped column and *any other* numeric column | Relationship flagging (RULE-005) — fires once per correlated pair found |
| `anomaly_count` | Count of already-flagged anomalies in the scoped column (optionally filtered by `method_filter`) | Repeated-breach escalation (RULE-004) |
| `isolation_forest_flag` | Boolean — was this specific row flagged by Isolation Forest? | Multivariate anomaly (RULE-006) — evaluated per-row, not per-column |

### Rule evaluation order
Rules are evaluated in the order they appear in the JSON array, independently of one another (FR-044
— no chaining). If a malformed rule is encountered (missing required field, invalid `operator`, or
invalid `metric`), skip that single rule, log a warning, and continue evaluating the rest — do not
abort the whole rule file (FR-048).

---

## 4. Statistics & Detection Algorithm Parameters (fills FR-021–FR-040)

### Z-score outliers (FR-031)
```
z = (value - column_mean) / column_std_dev   # std_dev uses ddof=1 (sample std, i.e. pandas' default .std())
flag if abs(z) > settings.detection.zscore_threshold   # default 3.0
```

### IQR outliers (FR-032)
```
Q1, Q3 = 25th and 75th percentile of the column
IQR = Q3 - Q1
lower_bound = Q1 - (settings.detection.iqr_multiplier * IQR)   # default multiplier 1.5
upper_bound = Q3 + (settings.detection.iqr_multiplier * IQR)
flag if value < lower_bound or value > upper_bound
```

### Isolation Forest (FR-033)
```python
from sklearn.ensemble import IsolationForest
model = IsolationForest(
    contamination=settings.detection.isolation_forest_contamination,  # default 0.05
    n_estimators=settings.detection.isolation_forest_n_estimators,     # default 100
    random_state=settings.detection.isolation_forest_random_state,     # default 42 — fixed for reproducibility
)
predictions = model.fit_predict(dataframe[selected_numeric_columns])
# predictions == -1  => flagged as an anomaly (this row's isolation_forest_flag = true)
```
Run Isolation Forest across **all selected numeric columns simultaneously** (it is inherently
multivariate) — never one column at a time; that's what Z-score/IQR are for.

### Trend Analysis (FR-024, FR-036)
1. **Identify the sequence axis**: use a `datetime`-typed column if one exists; otherwise fall back to
   row order (the dataframe's positional index, or an explicit sequence column such as `Sample_ID`).
2. **Moving average window**:
   ```
   window = clamp(
       round(row_count * settings.statistics.trend_window_fraction_of_dataset),  # default fraction 0.1
       settings.statistics.trend_window_min_samples,   # default 3
       settings.statistics.trend_window_max_samples,   # default 20
   )
   ```
3. **Slope**: `slope, intercept = numpy.polyfit(sequence_index, column_values, deg=1)`
4. **Direction classification** (used in both trend patterns and NLG, §5):
   ```
   total_predicted_change = slope * row_count
   bar = settings.statistics.trend_stability_std_multiplier * column_std_dev   # default multiplier 0.5
   direction = "Increasing" if total_predicted_change > bar
             else "Decreasing" if total_predicted_change < -bar
             else "Stable"
   ```

### Correlation (FR-025, FR-026)
Pearson correlation (`dataframe[numeric_cols].corr()`), all pairs. A pair is "strong" if
`abs(r) > settings.statistics.correlation_threshold` (default `0.7`).

### Severity Assignment (FR-038)
Severity comes from **whichever rule or detection method produced the finding**:
- Rule-based findings: severity is whatever the rule's own `severity` field says (§3).
- Raw Z-score/IQR outliers with **no matching rule**: default to `Warning`. (A dedicated rule such as
  RULE-001 can override this to `Critical` for a specific column, as shown in the seed rule file.)
- Isolation Forest flags with no matching rule: default to `Warning`.

---

## 5. Natural Language Generation Templates (fills FR-051–FR-058)

These are literal Python `str.format()`-style templates. Using exactly these (rather than inventing new
wording per finding) is what keeps FR-056 (no duplicate/contradictory phrasing) achievable — one
template per finding *type*, always.

```python
TEMPLATES = {
    "dataset_summary":
        "The dataset '{filename}' contains {row_count} rows across {column_count} columns, "
        "imported on {import_date}.",

    "zscore_anomaly":
        "Column '{column}' shows an unusual value of {value} at row {row}, which is {z_score} "
        "standard deviations from the mean — flagged as a statistical outlier ({severity}).",

    "iqr_anomaly":
        "Column '{column}' has a value of {value} at row {row} that falls outside the expected "
        "range (below {lower_bound} or above {upper_bound}) — flagged as an outlier ({severity}).",

    "isolation_forest_anomaly":
        "Row {row} was flagged as an unusual combination of values across {columns_involved} — "
        "this pattern does not resemble the rest of the dataset ({severity}).",

    "trend_pattern":
        "Column '{column}' shows a {direction} trend over the dataset (slope = {slope}).",

    "correlation_pattern":
        "Columns '{column_a}' and '{column_b}' are strongly correlated (r = {r_value}), "
        "suggesting a possible relationship worth investigating.",

    "rule_fired":
        "{conclusion_text} (triggered because {matched_on}).",

    "recommendation":
        "{severity}: {recommendation_text} (Source: {source_reference}).",

    "no_findings_conclusion":
        "No significant anomalies, threshold breaches, or rule matches were found in this dataset. "
        "The data appears to be within expected engineering parameters.",
}
```

**Deduplication rule (FR-056):** before adding a generated sentence to the Findings section, check
whether a sentence referencing the same `(column, finding_type)` pair already exists in the current
session's insight list; if so, skip the duplicate rather than adding a second near-identical sentence.

---

## 6. File Format Detection & Parsing (fills FR-005, FR-006)

### Detection order
1. Trust the file extension if it is one of `.csv`, `.xlsx`, `.xls`, `.json`, `.txt`, `.log`.
2. If the extension is missing or unrecognized, sniff the content:
   - Starts with `{` or `[` (after stripping whitespace) → treat as **JSON**.
   - First 20 non-empty lines: if more than 50% match the LOG_LINE_PATTERN below → treat as **LOG**.
   - Otherwise → attempt **CSV/TXT** parsing (see delimiter sniffing below).
   - If all of the above fail, or the file is a `.xlsx`/`.xls` binary structure → treat as **Excel**.

### Delimiter sniffing for CSV/TXT (FR-004)
Use Python's `csv.Sniffer().sniff(sample)` on the first ~10 lines. If sniffing raises an exception,
fall back to trying delimiters in this priority order and using the first one that produces a
consistent column count across all sampled lines: `[',', '\t', ';', '|']`. If none work, default to
comma and let row-validation (FR-011) surface the resulting error.

### LOG line pattern (FR-005)
```python
import re
LOG_LINE_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)\s+'
    r'(?P<level>[A-Z]{4,8})\s+(?P<message>.*)$'
)
```
Matches lines like `2026-07-11 08:15:32 INFO Engine started` or `2026-07-11T08:15:32.123 WARNING ...`.

- **Matched lines** become rows with columns `timestamp`, `level`, `message`.
- **Unmatched lines** (within an otherwise-matching file) become rows with `timestamp=NaT`,
  `level="UNKNOWN"`, `message=<the full raw line>` — never silently dropped.
- If **fewer than 50%** of lines match at all, treat the entire file as unstructured: ingest it as a
  single `raw_line` text column (one row per line), skip numeric statistics entirely for it, and run
  only frequency-distribution analysis (FR-027) if the user still wants some insight into it.

---

## 7. GUI Layout Specification (fills FR-081–FR-090)

| Property | Value |
|---|---|
| Default window size | 1440 × 900 px |
| Minimum window size | 1280 × 800 px (below this, panels may not render usably) |
| Sidebar width (expanded) | 220 px, fixed |
| Sidebar width (collapsed, icon-only) | 60 px |
| Base font | System default UI font (Segoe UI on Windows 10/11) |
| Body text size | 10 pt |
| Section header size | 14 pt |
| Page/panel title size | 18 pt |
| Sidebar items | Import, Analysis, History, Settings — in that fixed top-to-bottom order (FR-082) |
| Tabs | One tab per open dataset session, added to the top of the main content area (FR-085) |
| Color tokens | All taken from `color_philosophy.md` §"The Palette" and §"Severity Color Mapping" — never inline hex codes scattered through panel files (see `code_hygiene_guide.md` §3) |

---

## 8. PDF Report Layout Specification (fills FR-071–FR-080)

| Property | Value |
|---|---|
| Page size | A4, portrait |
| Margins | 2 cm on all sides |
| Title font | Helvetica-Bold, 22 pt |
| Section header font | Helvetica-Bold, 14 pt |
| Body font | Helvetica, 10 pt |
| Footer/disclaimer font | Helvetica-Oblique, 8 pt |
| Section order (fixed) | 1) Cover/Header (FR-072) → 2) Table of Contents *(only if 3+ sections, FR-073)* → 3) Statistical Summary → 4) Engineering Findings, grouped by column/subsystem (FR-054) → 5) Conclusion (FR-059) → 6) Recommendations, ranked Critical→Warning→Info (FR-061) → 7) Graphs *(optional, toggle-able, FR-069)* → disclaimer footer repeated on every page (FR-079) |
| Filename convention | `{dataset_name_sanitized}_{session_id}_{YYYYMMDD_HHMMSS}.pdf` — e.g. `engine_test_run_S00042_20260711_143205.pdf`. (`dataset_name_sanitized` = original filename without extension, non-alphanumeric characters replaced with `_`.) This refines the shorthand `{SessionID}_{Timestamp}.pdf` shown in `hld.md`. |
| Disclaimer footer text | *"This report was generated with AI-assisted analysis (AEIA). Findings and recommendations are advisory and require review and sign-off by a qualified engineer before any operational decision is made."* |

---

## 9. Standard Error Messages (fills FR-084)

| Situation | Exact User-Facing Message |
|---|---|
| File cannot be parsed at all | "This file could not be read. It may be corrupted or in an unsupported format. Please check the file and try again." |
| Recognized but unsupported extension | "This file type isn't supported yet. AEIA currently supports CSV, XLSX, JSON, TXT, and LOG files." |
| Dataset has zero rows | "This file appears to be empty. Please import a file that contains data." |
| Inconsistent column count per row | "Some rows in this file have a different number of columns than the header (first seen at row {row_number}). Please check the file's formatting." |
| Rule file fails to parse | "The rule file (engineering_rules.json) could not be loaded due to a formatting error: {error_detail}. The default rule set will be used instead." |
| Report export fails (e.g. permissions, missing folder) | "The report could not be saved to the selected location. Please check that the folder exists and that you have permission to write to it." |
| Settings validation fails (e.g. negative threshold) | "Please enter a positive number for this setting." |

All messages are plain sentences with **no raw stack trace or exception class name** shown to the
user; the full technical error (if any) goes only into the error log file
(`%APPDATA%\AEIA\aeia_error.log`, per `packaging_deployment_guide.md` §9).

---

## 10. Cross-Reference Index

| If you're implementing... | Read this section |
|---|---|
| `core/data_loader.py` | §6 |
| `core/preprocessor.py` | §2 (fill constants), §9 (validation messages) |
| `core/statistics_engine.py` | §4 |
| `core/anomaly_detector.py` | §4 |
| `core/expert_system.py` | §3 |
| `core/insight_generator.py` | §5 |
| `core/recommendation_engine.py` | §5, §4 (severity) |
| `core/report_builder.py` | §8 |
| `gui/*.py` | §7 |
| `database/schema.sql` | `technical_design.md` Part A (extracted verbatim into `seed_files/schema.sql`) |
| Anything involving default config values | §2, `seed_files/settings.json` |
| Anything involving the starter rules | §3, `seed_files/engineering_rules.json` |
| Validating your implementation against real numbers | `sample_data/README.md` |
