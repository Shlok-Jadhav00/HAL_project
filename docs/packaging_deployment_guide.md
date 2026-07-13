# AEIA Packaging & Deployment Guide
## A Complete Beginner-Friendly Guide to Building and Distributing the Offline Desktop App

---

## Table of Contents
1. [What Problem Are We Solving?](#1-what-problem-are-we-solving)
2. [What is PyInstaller and Why Do We Need It?](#2-what-is-pyinstaller-and-why-do-we-need-it)
3. [Architecture Overview: One File, No Server](#3-architecture-overview-one-file-no-server)
4. [What Goes Into the Package](#4-what-goes-into-the-package)
5. [What is a `.spec` File?](#5-what-is-a-spec-file)
6. [Step-by-Step: Building on Your Development PC](#6-step-by-step-building-on-your-development-pc)
7. [Step-by-Step: Transferring to USB](#7-step-by-step-transferring-to-usb)
8. [Step-by-Step: Running on the Offline Engineer's PC](#8-step-by-step-running-on-the-offline-engineers-pc)
9. [Day-to-Day Operations](#9-day-to-day-operations)
10. [Updating the App in the Future](#10-updating-the-app-in-the-future)
11. [Troubleshooting FAQ](#11-troubleshooting-faq)

---

## 1. What Problem Are We Solving?

AEIA needs **Python and about a dozen libraries** (PyQt5, Pandas, NumPy, SciPy, scikit-learn,
ReportLab, Matplotlib, NLTK/spaCy) to run.

The engineer's PC — often on an air-gapped or restricted network with no internet access — will
almost certainly **not have Python installed**, and because it has no internet, it cannot `pip install`
anything either.

**PyInstaller** solves this: it packages the Python interpreter, every required library, and our own
code into a single self-contained `.exe` file. The engineer's PC needs nothing else installed.

---

## 2. What is PyInstaller and Why Do We Need It?

Think of PyInstaller like **vacuum-sealing a full meal kit**:

```
┌─────────────────────────────────────────────────────────┐
│  AEIA.exe (PyInstaller Bundle)                          │
│                                                          │
│  Inside this single file:                                │
│  ✅ Python 3.x interpreter (embedded)                     │
│  ✅ All libraries (PyQt5, Pandas, NumPy, SciPy, etc.)     │
│  ✅ Our code (main.py, core/, gui/, database/)            │
│  ✅ The default rules and settings files                  │
│                                                           │
│  The engineer's PC doesn't need Python at all!            │
│  Double-click, and it just runs.                          │
└─────────────────────────────────────────────────────────┘
```

**Key concepts explained simply:**

| Term | Real-World Analogy | Explanation |
|:---|:---|:---|
| **PyInstaller** | The vacuum-sealing machine | A tool that analyzes your Python code, finds every library it imports, and bundles them all together. |
| **`.spec` file** | The recipe card | A generated config file describing exactly what to include, what to exclude, and how to build the bundle. |
| **`.exe` (one-file build)** | The sealed meal kit | The final single executable file, ready to run on any compatible Windows machine. |
| **`dist/` folder** | The delivery box | Where PyInstaller places the finished `.exe` after a successful build. |
| **`build/` folder** | Packing scraps | Temporary working files PyInstaller creates during the build — safe to delete, not part of the final product. |

---

## 3. Architecture Overview: One File, No Server

This is the biggest difference from a networked system — there's nothing to orchestrate:

```
   Development PC (with internet)              Engineer's PC (fully offline)
   ┌─────────────────────────┐                 ┌──────────────────────────┐
   │  Python + venv           │                 │                          │
   │  All source code         │   PyInstaller   │   AEIA.exe               │
   │  (main.py, core/, gui/)  │ ──────────────▶ │   (double-click to run)  │
   │                          │   builds once   │                          │
   │  requirements.txt        │                 │   No Python needed       │
   └─────────────────────────┘                 │   No internet needed     │
                                                │   No server, no Docker   │
                                                └──────────────────────────┘
```

There are no containers, no `docker-compose.yml`, and no separate database server to start — the
SQLite database is just a file (`aeia.db`) that sits next to the `.exe` or in the app's data folder.

---

## 4. What Goes Into the Package

| Included | Not Included (and why) |
|---|---|
| Python interpreter | A code editor (not needed to *run* the app, only to develop it) |
| PyQt5, Pandas, NumPy, SciPy, scikit-learn, ReportLab, Matplotlib, NLTK/spaCy | Docker (no server components exist to containerize) |
| `main.py`, `core/`, `gui/`, `database/` | PostgreSQL (SQLite is embedded, no separate DB engine needed) |
| Default `config/settings.json` and `rules/engineering_rules.json` | Node.js (there's no separate frontend build step — PyQt5 *is* the frontend) |

---

## 5. What is a `.spec` File?

When you first run PyInstaller, it generates a `AEIA.spec` file. This is a plain Python config file that
controls the build — for example, telling PyInstaller to bundle `config/` and `rules/` as extra
"data files" (since PyInstaller doesn't automatically know about non-code files your app needs):

```python
# Excerpt from AEIA.spec — the important part for a beginner to understand
a = Analysis(
    ['main.py'],
    datas=[
        ('config/settings.json', 'config'),
        ('rules/engineering_rules.json', 'rules'),
        ('database/schema.sql', 'database'),
    ],
    ...
)
```

Once this `.spec` file exists, future builds use it directly instead of re-detecting everything from
scratch — this is why you'll see a `pyinstaller AEIA.spec` command in later builds, instead of
re-running the long command with all its flags.

---

## 6. Step-by-Step: Building on Your Development PC

These commands run on **your PC** — the one with internet, Python, and the project's virtual
environment set up.

### Step 1: Activate your virtual environment
```powershell
cd "C:\Users\Shlok\Projects\AEIA"
.venv\Scripts\activate
```

### Step 2: Install PyInstaller
```powershell
pip install pyinstaller
```

### Step 3: Build the executable (first time)
```powershell
pyinstaller --onefile --windowed --name AEIA ^
    --add-data "config/settings.json;config" ^
    --add-data "rules/engineering_rules.json;rules" ^
    --add-data "database/schema.sql;database" ^
    main.py
```
**What each flag means:**
- `--onefile`: bundle everything into a single `.exe` (instead of a folder of many files).
- `--windowed`: don't open a background console/terminal window alongside the GUI.
- `--add-data`: include a non-code file (config, rules, schema) inside the bundle.

This may take a few minutes the first time. PyInstaller will create a `dist/AEIA.exe` when it finishes.

### Step 4: Test it locally
```powershell
dist\AEIA.exe
```
The AEIA main window should open, exactly as it does with `python main.py`, but with no terminal
window behind it.

---

## 7. Step-by-Step: Transferring to USB

### Step 1: Gather the files
```
USB Drive/
├── AEIA.exe                  (~150-300 MB, includes everything)
└── README_INSTALL.txt        (simple instructions for the engineer)
```
That's it — unlike a Docker-based deployment, there's no separate database image, no
`docker-compose.yml`, and no multi-file transfer checklist. One `.exe` is the whole application.

### Step 2: Copy `AEIA.exe` to the USB drive
Simple drag-and-drop copy — no `docker save` step needed since there are no container images.

---

## 8. Step-by-Step: Running on the Offline Engineer's PC

### Step 1: Copy the exe to a permanent location
```powershell
mkdir C:\AEIA
copy D:\AEIA.exe C:\AEIA\
```

### Step 2: Run it
```powershell
C:\AEIA\AEIA.exe
```
Or simply double-click `AEIA.exe` in File Explorer.

### Step 3 (Optional): Create a desktop shortcut
Right-click `AEIA.exe` → **Send to** → **Desktop (create shortcut)**. This lets the engineer launch
AEIA the same way they'd launch any other installed program.

### Step 4: First-run data folder
On first launch, AEIA creates its data folder (default: `%APPDATA%\AEIA\`) containing `config/`,
`rules/`, `database/`, and `reports/` — copied from the bundled defaults. From then on, all settings,
rule edits, and history persist there, independent of the `.exe` itself.

---

## 9. Day-to-Day Operations

### Starting the app
Double-click `AEIA.exe`, or use the desktop shortcut. There's no service to start and no terminal
command to remember — it behaves like any other desktop program.

### Closing the app
Close the window as normal (File → Exit, or the window's close button). Nothing is left running in
the background afterward.

### Checking the version
Open the About/Help panel from within the app (FR-089) — it shows the current AEIA version.

### Viewing error logs
If something goes wrong, AEIA writes a log file to `%APPDATA%\AEIA\aeia_error.log` instead of showing
a raw Python traceback on-screen (FR-084). Attach this file if reporting a bug.

---

## 10. Updating the App in the Future

When you make changes to the code on your development PC:

1. **Rebuild** the executable:
   ```powershell
   pyinstaller AEIA.spec
   ```
   (Using the `.spec` file from now on, instead of retyping every flag.)
2. **Copy** the new `dist\AEIA.exe` to USB.
3. **Transfer** it to the offline PC and overwrite the old `C:\AEIA\AEIA.exe`.
4. **Restart** the app — the engineer's saved settings, rules, and history in `%APPDATA%\AEIA\` are
   untouched, since they live outside the `.exe` itself.

---

## 11. Troubleshooting FAQ

### Q: Windows shows "Windows protected your PC" (SmartScreen warning)
**A:** This is expected for a new, unsigned `.exe` from a small project — it isn't a sign of a virus.
Click **"More info"** → **"Run anyway"**. Getting rid of this warning permanently requires a paid code-
signing certificate, which is usually out of scope for a student/internal engineering tool.

### Q: Antivirus software flags or quarantines `AEIA.exe`
**A:** PyInstaller-built executables are sometimes falsely flagged because their bundling technique
resembles some malware packing methods. Add an exception for `AEIA.exe` in the antivirus settings, or
ask the IT administrator to whitelist it.

### Q: The app won't start, and there's no error message at all
**A:** Rebuild without `--windowed` temporarily (`pyinstaller --onefile --name AEIA main.py`) so a
console window appears alongside the GUI and shows the real error — most commonly a missing
`--add-data` entry for `config/`, `rules/`, or `database/schema.sql`.

### Q: The `.exe` is very large (100s of MB)
**A:** This is normal — Pandas, NumPy, SciPy, and scikit-learn are large libraries, and PyInstaller
bundles all of them plus the Python interpreter itself. This is the tradeoff for "no Python install
needed."

### Q: How do I back up an engineer's analysis history?
**A:** Copy the entire `%APPDATA%\AEIA\` folder — it contains `database/aeia.db` (all session history)
along with their configured settings and rules.

### Q: The engineer is on Windows 7 and the app won't launch
**A:** Current PyQt5 builds may not support Windows 7 reliably. See the Tkinter fallback plan
(FS-007) in `tech_stack_and_deployment_status.md`.

---

## Glossary for Non-Technical Readers

| Term | Simple Explanation |
|:---|:---|
| **Executable (`.exe`)** | A ready-to-run program file — no installation of other software required. |
| **PyInstaller** | A tool that packages a Python program and everything it needs into one file. |
| **Virtual environment (`venv`)** | An isolated folder of Python packages for one project, kept separate from other projects. |
| **`.spec` file** | A saved recipe describing exactly how to build the executable. |
| **SmartScreen** | A Windows security check for unfamiliar downloaded programs. |
| **Air-gapped** | A computer or network with no internet connection, isolated for security or practicality. |
| **`%APPDATA%`** | A standard Windows folder (per-user) where apps store their settings and data. |
