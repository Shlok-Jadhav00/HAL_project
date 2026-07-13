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
