# Test Cases Specification - AEIA

This document defines the test suite for validating the Functional Requirements (FR-001 to FR-105) of
AEIA. All tests are designed for manual validation by a beginner-level tester running the application
locally, offline, with no special hardware.

---

## 1. Test Suite Summary Table

| Test Case ID | FR ID | Module | Title | Test Procedure | Expected Result |
|---|---|---|---|---|---|
| **TC-001** | FR-001 | Import | CSV import | Click "Import", select a `.csv` file. | File loads; preview grid appears. |
| **TC-002** | FR-002 | Import | Excel import | Import a `.xlsx` file with multiple columns. | Loads correctly; sheet 1 used by default. |
| **TC-003** | FR-003 | Import | JSON import | Import a nested-array JSON file. | Flattened into a tabular preview. |
| **TC-004** | FR-004 | Import | TXT import | Import a comma-delimited `.txt` file. | Parsed as a table, same as CSV. |
| **TC-005** | FR-005 | Import | LOG import | Import a `.log` file with timestamped lines. | Parsed into rows via regex; unmatched lines flagged. |
| **TC-006** | FR-006 | Import | Format ambiguity | Import a `.txt` file with pipe-delimiters. | Prompted to confirm delimiter/format. |
| **TC-007** | FR-007 | Import | Preview grid | After import, look at the panel. | First rows shown before analysis starts. |
| **TC-008** | FR-008 | Import | Type detection | Import a dataset with a date column and a numeric column. | Columns tagged `datetime` and `numeric` respectively. |
| **TC-009** | FR-009 | Import | Column selection | Uncheck one column before analysis. | Excluded column does not appear in results. |
| **TC-010** | FR-010 | Import | Dataset metadata | Import any file, check History/DB. | New `datasets` row with filename, counts, timestamp. |
| **TC-011** | FR-011 | Preprocess | Structure validation | Import a file with a ragged row (extra column). | Clear error shown; import blocked or row flagged. |
| **TC-012** | FR-012 | Preprocess | Missing value report | Import a dataset with blank cells. | Per-column missing count/percentage displayed. |
| **TC-013** | FR-013 | Preprocess | Missing value strategy | Choose "Fill with mean" for a numeric column. | Blanks replaced with column mean. |
| **TC-014** | FR-014 | Preprocess | Duplicate removal | Import a dataset with 2 identical rows. | Duplicates removed; count shown ("2 duplicates removed"). |
| **TC-015** | FR-015 | Preprocess | Formatting normalization | Import mixed-case category values ("ok"/"OK"/"Ok"). | Offered a normalize option; values unified. |
| **TC-016** | FR-016 | Preprocess | Outlier pre-scan | Import a dataset with one extreme numeric value. | Warning shown before full analysis starts. |
| **TC-017** | FR-017 | Preprocess | Sanity range check | Configure a plausible range for "Temperature"; import out-of-range value. | Value flagged as implausible. |
| **TC-018** | FR-018 | Preprocess | Preprocessing log | Complete any cleaning step. | Actions listed; later appear in exported report. |
| **TC-019** | FR-019 | Preprocess | Undo preprocessing | Apply a cleaning step, click "Undo/Revert". | Dataset reverts to originally imported state. |
| **TC-020** | FR-020 | Preprocess | Raw file untouched | Run preprocessing, check the original file on disk. | Original file unchanged (checksum identical). |
| **TC-021** | FR-021 | Statistics | Basic stats | Run analysis on a numeric column. | Mean, median, mode, std dev, variance shown. |
| **TC-022** | FR-022 | Statistics | Min/Max/Range | Check results table. | Min, Max, Range values present and correct. |
| **TC-023** | FR-023 | Statistics | Quartiles/IQR | Check results table. | Q1, Q3, IQR shown per numeric column. |
| **TC-024** | FR-024 | Statistics | Trend analysis | Analyze a time-ordered numeric column. | Moving average / slope reported. |
| **TC-025** | FR-025 | Statistics | Correlation matrix | Analyze a dataset with 3+ numeric columns. | Pairwise Pearson correlation matrix displayed. |
| **TC-026** | FR-026 | Statistics | Correlation highlight | Include two columns with `r > 0.7`. | Pair highlighted as a candidate relationship. |
| **TC-027** | FR-027 | Statistics | Frequency distribution | Analyze a categorical column. | Frequency table/chart of category counts shown. |
| **TC-028** | FR-028 | Statistics | Grouped stats | Group by a categorical column (e.g. Sensor ID). | Stats computed per group. |
| **TC-029** | FR-029 | Statistics | Performance budget | Analyze a 100,000-row dataset on minimum-spec hardware. | Completes within 10 seconds. |
| **TC-030** | FR-030 | Statistics | Results tab | Open Results tab after analysis. | Sortable table of all statistics displayed. |
| **TC-031** | FR-031 | Anomaly | Z-score detection | Analyze a column with one value >3 std devs from mean. | Flagged as a Z-score anomaly. |
| **TC-032** | FR-032 | Anomaly | IQR detection | Analyze a column with a value beyond 1.5xIQR. | Flagged as an IQR anomaly. |
| **TC-033** | FR-033 | Anomaly | Isolation Forest | Run multivariate detection on 3+ numeric columns. | Multivariate anomalies flagged, distinct from single-column outliers. |
| **TC-034** | FR-034 | Anomaly | Method selection | Deselect "Isolation Forest" before running. | Only Z-score/IQR results appear. |
| **TC-035** | FR-035 | Anomaly | Anomaly listing | Open Findings after detection. | Each anomaly shows row ref, column(s), method. |
| **TC-036** | FR-036 | Anomaly | Pattern detection | Analyze a column with a sustained upward drift. | Drift pattern reported. |
| **TC-037** | FR-037 | Anomaly | Threshold breach | Run RULE-001 ("Engine_Temp_C > 120") against `sample_data/engine_test_run.csv`. | `Sample_ID` 45 (134.5) flagged as a breach, linked to RULE-001 — see `sample_data/README.md` §6–7. |
| **TC-038** | FR-038 | Anomaly | Severity assignment | Check any flagged anomaly. | Labeled Info, Warning, or Critical. |
| **TC-039** | FR-039 | Anomaly | False positive marking | Mark an anomaly "False Positive". | Removed from Conclusion/Recommendations on regenerate. |
| **TC-040** | FR-040 | Anomaly | CPU-only run | Run detection with no GPU present. | Completes normally; no GPU-related errors. |
| **TC-041** | FR-041 | Rules | Rule file load | Start the app with the default rule file present. | Rules load without error at startup. |
| **TC-042** | FR-042 | Rules | Condition types | Add a rule referencing `std_dev > threshold`. | Rule evaluates correctly against a matching session. |
| **TC-043** | FR-043 | Rules | Rule evaluation | Complete analysis on a dataset matching a rule. | Rule fires and appears in Findings. |
| **TC-044** | FR-044 | Rules | No rule chaining (documented limitation) | Create two rules where Rule B's condition depends on Rule A having fired (e.g. Rule B checks "RULE-001 fired"). | Rule B does NOT fire based on Rule A firing — each rule evaluates only against session statistics/anomalies, never against other rules' outcomes. This confirms the limitation is real, not accidentally implemented. |
| **TC-045** | FR-045 | Rules | Rule editing via UI | Add a new rule from Settings; re-run analysis. | New rule is evaluated in the next session. |
| **TC-046** | FR-046 | Rules | Fired-rule logging | Check a session where a rule fired. | Rule ID and trigger condition logged. |
| **TC-047** | FR-047 | Rules | Starter rule set | Inspect `engineering_rules.json` on first run. | Contains a non-empty default set of rules. |
| **TC-048** | FR-048 | Rules | Malformed rule file | Introduce a JSON syntax error in the rule file, restart app. | Clear error shown; app does not crash. |
| **TC-049** | FR-049 | Rules | Rule scoping | Scope a rule to columns matching `Temp*`. | Rule only evaluates against matching columns. |
| **TC-050** | FR-050 | Rules | Rule performance | Load 100 rules, run evaluation. | Completes within 2 seconds. |
| **TC-051** | FR-051 | Insights | Dataset summary | Complete any analysis. | Plain-language dataset summary shown. |
| **TC-052** | FR-052 | Insights | Anomaly description | View Findings for a session with anomalies. | Each anomaly has an engineering-language sentence. |
| **TC-053** | FR-053 | Insights | Rule description | View Findings for a session with fired rules. | Each fired rule has a plain-language explanation. |
| **TC-054** | FR-054 | Insights | Grouped findings | View the Findings section. | Findings grouped by column/subsystem. |
| **TC-055** | FR-055 | Insights | Template-based NLG | Inspect any generated sentence. | Wording matches known templates; no external API call made (check network monitor). |
| **TC-056** | FR-056 | Insights | No duplicate statements | Trigger two findings on the same column. | Summary does not repeat the same sentence twice. |
| **TC-057** | FR-057 | Insights | Regenerate after FP | Mark a false positive, click "Regenerate Summary". | Summary updates, excluding the false positive. |
| **TC-058** | FR-058 | Insights | Offline generation | Disconnect network adapter, run analysis. | Summary generates normally with no errors. |
| **TC-059** | FR-059 | Conclusion | Overall conclusion | Complete a session with findings. | A single synthesized Conclusion statement is shown. |
| **TC-060** | FR-060 | Conclusion | Recommendations | Complete a session with a fired rule. | At least one Recommendation tied to that finding. |
| **TC-061** | FR-061 | Conclusion | Severity ranking | View Recommendations list. | Critical items listed before Warning/Info. |
| **TC-062** | FR-062 | Conclusion | Engineer notes | Add a free-text note to a finding. | Note is saved and appears in the exported report. |
| **TC-063** | FR-063 | Conclusion | Recommendation traceability | Inspect any recommendation. | Source rule/method is referenced. |
| **TC-064** | FR-064 | Conclusion | No findings case | Analyze a clean dataset with no anomalies. | Conclusion reads "No significant findings" (not blank). |
| **TC-065** | FR-065 | Conclusion | Editable before export | Edit the Conclusion text field before exporting. | Edited text appears in the final PDF. |
| **TC-066** | FR-066 | Visualization | Trend chart | View charts for a time-ordered column with anomalies. | Line chart with anomalies highlighted. |
| **TC-067** | FR-067 | Visualization | Histogram | Select a numeric column for charting. | Histogram displayed. |
| **TC-068** | FR-068 | Visualization | Correlation heatmap | View charts with 3+ numeric columns. | Heatmap of correlation values shown. |
| **TC-069** | FR-069 | Visualization | Toggle charts | Disable "Include Charts" before export. | Report generated as text-only, no charts. |
| **TC-070** | FR-070 | Visualization | Offline chart generation | Disconnect network, generate charts. | Charts render normally with no errors. |
| **TC-071** | FR-071 | Report | Full PDF export | Click "Export Report" after a completed session. | PDF contains Summary, Findings, Conclusion, Recommendations, Graphs. |
| **TC-072** | FR-072 | Report | Report header | Open an exported PDF. | Header shows dataset name, timestamp, app version. |
| **TC-073** | FR-073 | Report | Table of contents | Export a report with 4+ sections. | TOC page present and links/labels match section order. |
| **TC-074** | FR-074 | Report | On-screen preview | Click "Preview" before exporting. | Report preview shown without writing a file yet. |
| **TC-075** | FR-075 | Report | Save location | Export and choose a custom folder/filename. | PDF saved at the chosen location with chosen name. |
| **TC-076** | FR-076 | Report | Re-export after edits | Edit a note, click "Export" again (no re-analysis). | New PDF reflects the edited note. |
| **TC-077** | FR-077 | Report | Offline report generation | Disconnect network, export a report. | Report generates successfully with no errors. |
| **TC-078** | FR-078 | Report | Export performance | Export a standard session's report on minimum-spec hardware. | Completes within 15 seconds. |
| **TC-079** | FR-079 | Report | Disclaimer footer | Open any exported PDF. | Footer includes AI-assisted/sign-off disclaimer. |
| **TC-080** | FR-080 | Report | CSV export | Click "Export Statistics as CSV". | CSV file with raw statistical results is created. |
| **TC-081** | FR-081 | GUI | Guided workflow | Open the app fresh. | Workflow steps (Import -> ... -> Export) are visually clear/ordered. |
| **TC-082** | FR-082 | GUI | Sidebar navigation | Click each sidebar item. | Import, Analysis, History, Settings views load correctly. |
| **TC-083** | FR-083 | GUI | Progress indicator | Run analysis on a large dataset. | Progress bar/spinner shown during processing. |
| **TC-084** | FR-084 | GUI | Friendly error messages | Attempt to import a corrupted file. | Plain-language error shown, no raw stack trace. |
| **TC-085** | FR-085 | GUI | Multiple sessions | Import two datasets in separate tabs. | Both remain open and independently analyzable. |
| **TC-086** | FR-086 | GUI | Status bar | Complete an analysis. | Status bar shows dataset name, row count, last analysis time. |
| **TC-087** | FR-087 | GUI | Keyboard shortcuts | Press `Ctrl+O` and `Ctrl+E`. | Import dialog opens; Export Report triggers respectively. |
| **TC-088** | FR-088 | GUI | UI responsiveness | Run a long analysis, try clicking elsewhere in the app. | UI stays responsive; not frozen. |
| **TC-089** | FR-089 | GUI | About/Help panel | Open About/Help from the menu. | Version and basic usage instructions shown. |
| **TC-090** | FR-090 | GUI | PyQt5 confirmed | Inspect running app. | Interface renders via PyQt5 (not a browser window). |
| **TC-091** | FR-091 | Settings | Threshold config | Change Z-score threshold to 2.5, re-run detection. | Anomaly count changes to reflect new threshold. |
| **TC-092** | FR-092 | Settings | Rule management UI | Disable a rule from Settings, re-run analysis. | Disabled rule no longer fires. |
| **TC-093** | FR-093 | Settings | Default report folder | Change default report folder, export a report. | Report saved to the new default location. |
| **TC-094** | FR-094 | Settings | Correlation threshold | Change correlation threshold to 0.5, re-analyze. | More pairs highlighted as correlated. |
| **TC-095** | FR-095 | Settings | JSON persistence | Change any setting, restart the app. | Setting change persists via `settings.json`. |
| **TC-096** | FR-096 | Settings | Restore defaults | Click "Restore Defaults". | All settings revert to factory values. |
| **TC-097** | FR-097 | Settings | Input validation | Enter a negative number for a threshold. | Rejected with a validation message. |
| **TC-098** | FR-098 | History | Session persistence | Complete a session. | New row appears in History with dataset name/timestamp/findings count. |
| **TC-099** | FR-099 | History | Sortable history | Open History with 3+ sessions. | List sortable by date. |
| **TC-100** | FR-100 | History | Re-open session | Click a past session in History. | Findings/report reload without re-running analysis. |
| **TC-101** | FR-101 | History | Re-export from history | Open a past session, click "Export Report" again. | Report re-generated/re-saved successfully. |
| **TC-102** | FR-102 | History | Delete session | Delete a session record, confirm. | Record removed from History (with confirmation prompt shown first). |
| **TC-103** | FR-103 | History | No raw file storage | Inspect the AEIA data folder after several sessions. | No copies of original dataset files found, only DB/report data. |
| **TC-104** | FR-104 | History | Persistence across restarts | Restart the app after completing sessions. | History still shows prior sessions. |
| **TC-105** | FR-105 | History | Scale check | Seed 500 history records (test script). | History view remains responsive, no significant slowdown. |

---

## 2. Non-Functional Spot Checks

| Test Case ID | NFR ID | Test Procedure | Expected Result |
|---|---|---|---|
| **TC-N01** | NFR-001 | Disconnect all network adapters, use the app fully end-to-end. | No feature fails or hangs waiting on a network call. |
| **TC-N02** | NFR-002 | Run on a machine matching minimum hardware spec (i3/4GB RAM, no GPU). | App runs and completes analysis without GPU errors. |
| **TC-N03** | NFR-003 | Run TC-029 (100k-row statistics), TC-050 (100-rule evaluation), and TC-078 (report export) together in sequence. | Each stays within its documented timing budget (10s / 2s / 15s respectively). |
| **TC-N04** | NFR-004 | Build the PyInstaller `.exe` and run it on a clean Windows 10 (64-bit) machine and a clean Windows 11 (64-bit) machine. | App launches and functions identically on both. |
| **TC-N05** | NFR-005 | Open `core/anomaly_detector.py` (or any `core/` module) cold, with no other context. | A developer unfamiliar with the file can identify its purpose from comments/FR references within a few minutes — see `code_hygiene_guide.md` Rule 1. |
| **TC-N06** | NFR-006 | Pick any finding shown in the Findings section. | It can be traced back to a specific statistic, detection method, or rule ID — never an unexplained assertion. |
| **TC-N07** | NFR-007 | Monitor outbound network traffic during a full session. | Zero outbound connections observed. |
| **TC-N08** | NFR-008 | Feed the app a deliberately malformed file (truncated CSV, corrupted XLSX, invalid JSON). | App shows a friendly error (see `implementation_specification.md` §9) instead of crashing. |
| **TC-N09** | NFR-009 | Give a first-time user (unfamiliar with the app) `sample_data/engine_test_run.csv` and no instructions beyond "generate a report." | They complete Import → Export without needing a manual, guided by the FR-081 workflow. |
| **TC-N10** | NFR-010 | Add a new file format loader (e.g. a stub `.xml` loader) and a new rule to `engineering_rules.json`. | Both can be added without modifying unrelated modules. |
| **TC-N11** | NFR-011 | Run the PyInstaller-built `.exe` on a clean machine with no Python installed. | Application launches and runs normally. |
| **TC-N12** | NFR-012 | Inspect `requirements.txt` / `requirements.lock.txt`. | Exact versions are pinned in the lock file per the process in `seed_files/requirements.txt`. |

---

## 3. Ground-Truth Validation Dataset

`sample_data/engine_test_run.csv` (61 rows) is a deterministic dataset built specifically for
validating TC-001 through TC-068 with **real expected numbers** instead of vague pass/fail judgment
calls. Full expected statistics, anomalies, correlations, and rule firings are documented in
`sample_data/README.md` — run this file through the app first and diff your output against that
document before testing with any other data.
