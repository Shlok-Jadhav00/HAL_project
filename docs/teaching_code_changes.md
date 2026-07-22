# Learning Guide: Code Changes & Problem Solving

Welcome to your technical deep-dive log! This document is where we'll walk through **real** bugs
encountered while building AEIA, the thinking process used to diagnose them, and the line-by-line code
changes made to fix them.

Think of this as a behind-the-scenes look at how software debugging actually works — updated
continuously as development proceeds.

---

## How to Use This Document

Every time we hit and fix a real bug during development, add a new dated entry below using this format:

```
## [YYYY-MM-DD] The "Short Description" Bug
**The Problem:** What you observed (the symptom, in plain language).

**The Thinking Process:**
1. What clue told us where to look?
2. What did we check first, and what did we find?
3. What was the root cause?

**The Fix:**
```language
// BEFORE (Buggy)
...

// AFTER (Fixed)
...
```

**The Lesson:** The general programming principle this bug illustrates, so it's useful beyond just
this one fix.
```

> ⚠️ **Important:** Entries in this file must describe bugs that were **actually encountered and
> fixed** in this project — never invented ones. A fabricated "war story" teaches the wrong lesson and
> undermines trust in the rest of the log. Since no code has been written yet (the project is still at
> the documentation/design stage — see `changelog.md`), this file currently has no real entries.

---

## Illustrative Example (Not a Real Bug — Shown Only to Demonstrate the Format)

## [Example] The "Silent Freeze" on Large File Import
**The Problem:** Importing a large CSV appears to hang the whole window — no progress bar, no
response to clicks — until it suddenly finishes.

**The Thinking Process:**
1. A frozen-but-not-crashed PyQt5 window almost always means a long operation is running on the
   **main GUI thread**, which also handles all mouse/keyboard events.
2. We'd check whether `data_loader.py`'s file-parsing call is being invoked directly from a button's
   click handler in `import_panel.py`, instead of on a background `QThread`.
3. If so, the parser blocking the main thread explains exactly why the whole window stops responding
   until parsing finishes.

**The Fix (in `gui/import_panel.py`):**
```python
# BEFORE (Buggy — runs on the main GUI thread)
def on_import_clicked(self):
    df = data_loader.load_dataset(file_path)  # blocks the whole UI while this runs
    self.show_preview(df)

# AFTER (Fixed — runs on a background thread)
def on_import_clicked(self):
    self.worker = ImportWorker(file_path)
    self.worker.finished.connect(self.show_preview)
    self.worker.start()
```

**The Lesson:** In a GUI application, anything that can take more than a fraction of a second
(reading a large file, running a model, generating a PDF) needs to run off the main thread, or the
whole interface will appear frozen — this is exactly why FR-088 requires background threading for
long-running operations.

---

*Real entries will be added above this line as actual development issues are found and fixed.*

---

## [2026-07-13] The "Shortcut Not Firing" Bug
**The Problem:** Pressing `Ctrl+O` or `Ctrl+E` did not trigger the file dialogs if the user was focused on a `QTableWidget` or text editor in the app.

**The Thinking Process:**
1. We originally set the shortcuts on `QAction` objects inside a `QMenu` using `import_action.setShortcut('Ctrl+O')`.
2. By default, a PyQt5 `QAction` uses `Qt.WindowShortcut` context. However, if a child widget (like a table) consumes the keyboard event, the action is bypassed.
3. Overriding `keyPressEvent` on the main window also fails because the main window doesn't receive the event if the child widget doesn't ignore it.

**The Fix (in `gui/main_window.py`):**
```python
# BEFORE (Buggy)
import_action = QAction('&Import Dataset...', self)
import_action.setShortcut('Ctrl+O')
import_action.triggered.connect(lambda: self._switch_panel(0))

# AFTER (Fixed)
import_action = QAction('&Import Dataset...', self)
import_action.setShortcut(QKeySequence('Ctrl+O'))
import_action.setShortcutContext(Qt.ApplicationShortcut)
import_action.triggered.connect(self._trigger_import)
```

**The Lesson:** For global application shortcuts in PyQt5 that must bypass child widget focus stealing, always set the context to `Qt.ApplicationShortcut`.

---

## [2026-07-13] The "Phantom Analysis Results" Bug
**The Problem:** When opening multiple dataset tabs, switching between the tabs did not visually update the analysis panel (the graphs and tables showed the original dataset's results).

**The Thinking Process:**
1. We noticed that tab switching correctly updated the active `session_id` internally, but nothing on screen changed.
2. The UI logic wasn't reloading the stored `analysis_results` from memory back into the tables when a tab was clicked.

**The Fix (in `gui/analysis_panel.py`):**
```python
# BEFORE (Buggy)
def set_session_data(self, data: Dict[str, Any]):
    self.session_data = data
    self.run_btn.setEnabled(True)

# AFTER (Fixed)
def set_session_data(self, data: Dict[str, Any]):
    self.session_data = data
    self.run_btn.setEnabled(True)
    
    if 'analysis_results' in data:
        self._on_analysis_finished(data['analysis_results'])
    else:
        self._clear_ui()
```

**The Lesson:** Data-binding isn't automatic in PyQt5. When switching active contexts, you must explicitly clear and repopulate the widgets with the new state.

---

## [2026-07-13] The "Empty History Rows" Bug
**The Problem:** The History panel showed the first row correctly, but all subsequent rows in the table were totally empty, and the status remained "In Progress" forever.

**The Thinking Process:**
1. The fact that the first row populated but the second row was entirely blank implied an invisible exception breaking the table population loop.
2. Inspecting the `_populate_table` loop revealed `sid = session.get('session_id')`. However, the database returns objects (Records), not dictionaries!
3. The `AttributeError` crashed the loop silently, leaving the remaining rows unpopulated.
4. Additionally, the status was permanently "In Progress" because the Analysis thread never updated the database when it finished!

**The Fix (in `gui/history_panel.py` and `gui/analysis_panel.py`):**
```python
# BEFORE (Buggy - history_panel.py)
sid = session.get('session_id')

# AFTER (Fixed)
sid = session.session_id
```

```python
# AFTER (Fixed - analysis_panel.py)
def _on_analysis_finished(self, results: Dict[str, Any]):
    # Save to history db
    if self.db_manager:
        session = self.session_data
        sid = session.get('session_id')
        # ... logic updated to handle database updates
```

**The Lesson:** Always be careful with ORM / database layer return types. Never assume you're getting a standard dictionary back from a database fetch method unless it's explicitly serialized first.

---

## [2026-07-22] The "Row Number Off-By-1" Bug
**The Problem:** The analysis report indicated an anomaly at row 44, but in the actual CSV viewed in Excel, the problematic data was on row 45.

**The Thinking Process:**
1. A row number discrepancy of exactly 1 or 2 usually indicates a 0-based versus 1-based indexing mismatch.
2. In `anomaly_detector.py`, the Z-score and IQR detectors were recording the index using `int(idx)`.
3. Pandas dataframes use 0-based indexing for data rows. However, when an engineer opens the CSV in Excel, the header occupies row 1, and the data starts at row 2. Therefore, pandas index 0 is Excel row 2 (offset of +2).

**The Fix (in `core/anomaly_detector.py`):**
```python
# BEFORE (Buggy)
for idx, val in series.items():
    if val < lower_bound or val > upper_bound:
        anomalies.append({
            'row_reference': int(idx),
            # ...
        })

# AFTER (Fixed)
for idx, val in series.items():
    if val < lower_bound or val > upper_bound:
        anomalies.append({
            'row_reference': int(idx) + 2,
            # ...
        })
```

**The Lesson:** Always map internal data-structure indices to the user's conceptual model. If the user views data in a spreadsheet, your row references must match the spreadsheet's coordinate system (1-based with headers).

---

## [2026-07-22] The "Duplicate Warning and Critical" Bug
**The Problem:** The same data point was marked as a Warning (by the statistical anomaly detector) and as a Critical (by the engineering rules), resulting in duplicate entries for the exact same event.

**The Thinking Process:**
1. The statistical anomaly detectors (Z-Score/IQR) run independently of the expert system rules. They both produce findings.
2. In `core/insight_generator.py`, the `seen` set for deduplicating only tracked `(column, finding_type)`. Since an anomaly is of type "Anomaly" and a rule match is of type "Rule", they were treated as distinct findings even if they flagged the identical row.
3. We needed a step in `_apply_confidence_matrix` to identify when both a statistical detector and a rule detector fired on the exact same `(col, row)` group, and drop the generic statistical finding in favor of the more specific rule finding.

**The Fix (in `core/insight_generator.py`):**
```python
# BEFORE (Buggy)
for (col, row), group in row_findings.items():
    # Loop over all insights in the group and update their severities
    for insight in group:
        # ...

# AFTER (Fixed)
for (col, row), group in row_findings.items():
    has_stats = len(stat_detectors) > 0
    has_rules = len(rule_detectors) > 0

    # If a rule matches and stats also flag it, keep only the rule
    if has_rules and has_stats:
        kept_insights = rule_detectors
    else:
        kept_insights = group

    for insight in kept_insights:
        # ... update severities and append to filtered_insights
```

**The Lesson:** When merging results from multiple independent diagnostic engines, always implement a unified deduplication/prioritization layer. Otherwise, overlapping evidence will spam the user with redundant alerts rather than increasing confidence.
