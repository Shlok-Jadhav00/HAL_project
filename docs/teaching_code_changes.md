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
# AFTER (Fixed - analysis_panel.py - DB tracking added)
if self.db_manager:
    self.db_manager.update_session(
        session_id=sid,
        status='Completed',
        findings_count=len(results.get('insights', []))
    )
```

**The Lesson:** Always be deeply aware of the data structures returned by ORMs/Database connectors. Treat objects as objects, and explicitly catch and log exceptions in UI loops so they don't silently swallow rendering failures.
