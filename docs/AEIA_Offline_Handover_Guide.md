# AEIA — Offline Handover & Recompilation Guide

**For the HAL team: How to modify the code and rebuild the `.exe` on an offline PC.**

---

## What's in This Handover Package

When Shlok hands over AEIA, you should receive a USB drive (or shared folder) containing:

```
USB Drive/
├── AEIA.exe                        # The compiled application (ready to use)
├── AEIA_Source/                     # Complete source code
│   ├── main.py
│   ├── core/
│   ├── gui/
│   ├── database/
│   ├── config/
│   ├── rules/
│   ├── docs/
│   ├── tests/
│   ├── sample_data/
│   ├── requirements.txt
│   ├── requirements.lock.txt       # Exact pinned versions
│   └── AEIA.spec                   # PyInstaller build recipe
│
├── Python_Installer/
│   └── python-3.10.11-amd64.exe    # Python installer for Windows
│
└── offline_packages/               # All dependency wheels (no internet needed)
    ├── PyQt5-5.15.11-*.whl
    ├── pandas-2.3.3-*.whl
    ├── numpy-2.2.6-*.whl
    ├── scipy-1.15.3-*.whl
    ├── scikit_learn-1.7.2-*.whl
    ├── matplotlib-3.10.9-*.whl
    ├── reportlab-5.0.0-*.whl
    ├── pyinstaller-6.21.0-*.whl
    ├── ... (all other dependencies)
    └── (~80 .whl files total)
```

---

## How to Prepare This Package (Shlok Does This Before Leaving)

**This step requires internet** — do it on your development PC before handover.

### Step 1: Download the Python Installer

1. Go to https://www.python.org/downloads/release/python-31011/
2. Download `python-3.10.11-amd64.exe` (the Windows 64-bit installer)
3. Save it to `USB Drive/Python_Installer/`

### Step 2: Download All Offline Packages

Open PowerShell in your AEIA project and run:
```powershell
.venv\Scripts\pip.exe download -r requirements.lock.txt -d offline_packages
```

This downloads every single `.whl` file that AEIA needs (~80 files) into the `offline_packages/` folder. These are self-contained binary packages — no internet is needed to install them later.

### Step 3: Copy the Source Code

Copy the entire `E:\AEIA\` folder (excluding `.venv/`, `build/`, `dist/`, `__pycache__/`) to the USB drive as `AEIA_Source/`.

### Step 4: Copy the Compiled `.exe`

Copy `E:\AEIA\dist\AEIA.exe` to the root of the USB drive.

---

## How to Set Up a Development Environment on an Offline PC

**This entire process requires zero internet.**

### Step 1: Install Python

1. Open `USB Drive/Python_Installer/`
2. Double-click `python-3.10.11-amd64.exe`
3. **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom of the installer
4. Click "Install Now"
5. Wait for installation to complete
6. Verify by opening Command Prompt and typing:
   ```cmd
   python --version
   ```
   You should see: `Python 3.10.11`

### Step 2: Copy the Source Code

Copy the `AEIA_Source/` folder from the USB drive to a permanent location on the PC, for example:
```
C:\AEIA\
```

### Step 3: Create a Virtual Environment

Open Command Prompt and run:
```cmd
cd C:\AEIA
python -m venv .venv
.venv\Scripts\activate
```

Your prompt should now show `(.venv)` at the beginning.

### Step 4: Install All Dependencies (Offline)

This is the key step — it installs everything from the local `.whl` files, not from the internet:
```cmd
pip install --no-index --find-links="D:\offline_packages" -r requirements.lock.txt
```

Replace `D:\offline_packages` with wherever the USB drive's `offline_packages/` folder is located.

This will take 1–2 minutes. When it finishes, every library AEIA needs is installed.

### Step 5: Install the spaCy Language Model (Offline)

The spaCy English model needs to be installed separately. Find the file `en_core_web_sm-3.8.0-py3-none-any.whl` in the `offline_packages/` folder and install it directly:
```cmd
pip install --no-index --find-links="D:\offline_packages" en_core_web_sm
```

### Step 6: Verify the Setup

Run AEIA from source to make sure everything works:
```cmd
.venv\Scripts\python.exe main.py
```

The AEIA window should open. If it does, the development environment is ready!

---

## How to Make Code Changes

### Editing the Code

Open any `.py` file in a text editor (Notepad, Notepad++, VS Code — whatever is available on the PC). The key folders are:

| If you want to change... | Edit files in... |
|:-------------------------|:-----------------|
| How data is imported | `core/data_loader.py` |
| How data is cleaned | `core/preprocessor.py` |
| How statistics are computed | `core/statistics_engine.py` |
| How anomalies are detected | `core/anomaly_detector.py` |
| Engineering rules (no code needed!) | `rules/engineering_rules.json` |
| How insights are worded | `core/insight_generator.py` |
| How the PDF report looks | `core/report_builder.py` |
| How the GUI looks | Files in `gui/` |
| Detection thresholds (no code needed!) | `config/settings.json` |

### Testing Your Changes

After making changes, test them by running:
```cmd
cd C:\AEIA
.venv\Scripts\activate
.venv\Scripts\python.exe main.py
```

The application will launch, and you can import a dataset and run analysis to verify your changes.

---

## How to Recompile Into a `.exe`

After you've made and tested your code changes, rebuild the executable:

### Step 1: Activate the Virtual Environment

```cmd
cd C:\AEIA
.venv\Scripts\activate
```

### Step 2: Build the `.exe`

```cmd
.venv\Scripts\pyinstaller.exe AEIA.spec
```

This uses the existing `AEIA.spec` build recipe to recompile everything. It takes about 2–3 minutes.

### Step 3: Find the New `.exe`

When the build completes, the new executable is at:
```
C:\AEIA\dist\AEIA.exe
```

### Step 4: Test It

Double-click `dist\AEIA.exe` to verify it works correctly.

### Step 5: Deploy

Copy the new `AEIA.exe` to the target engineer's PC (via USB drive, shared folder, etc.). That's it — no installation needed on the target PC.

---

## If You Added a New Data File to the Project

If you add a new non-code file that the application needs at runtime (e.g., a new JSON config file or a new SQL schema), you need to update `AEIA.spec` to include it:

1. Open `AEIA.spec` in a text editor
2. Find the `datas=` line
3. Add your new file. For example, to add `config/new_config.json`:

```python
datas=[
    ('config/settings.json', 'config'),
    ('config/new_config.json', 'config'),        # ← ADD THIS
    ('rules/engineering_rules.json', 'rules'),
    ('database/schema.sql', 'database'),
],
```

4. Save and recompile with `pyinstaller AEIA.spec`

---

## Common Changes That Do NOT Require Recompilation

These changes take effect immediately — just edit the file and restart the application:

| Change | File to Edit | Needs Recompile? |
|:-------|:-------------|:-----------------|
| Add/modify/disable an engineering rule | `%APPDATA%/AEIA/rules/engineering_rules.json` | **No** |
| Change detection thresholds (Z-Score, IQR) | `%APPDATA%/AEIA/config/settings.json` | **No** |
| Change the default report folder | `%APPDATA%/AEIA/config/settings.json` | **No** |

> **Note**: After the `.exe` has been run once, the *active* copies of `settings.json` and `engineering_rules.json` live in `%APPDATA%/AEIA/` (typically `C:\Users\<username>\AppData\Roaming\AEIA\`). Edit those files, not the ones in the source code folder.

---

## Troubleshooting

### "Python is not recognized as a command"
→ Python was installed without the "Add to PATH" checkbox. Reinstall Python and check that box.

### "pip install fails with 'No matching distribution found'"
→ Make sure you're pointing `--find-links` to the correct `offline_packages/` folder path. Use the full absolute path.

### "The `.exe` opens and immediately closes"
→ Run it from Command Prompt instead of double-clicking, so you can see the error message:
```cmd
cd C:\AEIA\dist
AEIA.exe
```

### "ModuleNotFoundError: No module named 'xyz'"
→ A dependency is missing. Install it from the offline packages:
```cmd
pip install --no-index --find-links="D:\offline_packages" xyz
```

### "I changed a file but the `.exe` still has the old behavior"
→ You need to recompile. Code changes to `.py` files only take effect in the `.exe` after running `pyinstaller AEIA.spec` again.

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║                    AEIA Quick Reference                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  RUN FROM SOURCE:                                            ║
║    cd C:\AEIA                                                ║
║    .venv\Scripts\activate                                    ║
║    .venv\Scripts\python.exe main.py                          ║
║                                                              ║
║  RECOMPILE TO .EXE:                                          ║
║    cd C:\AEIA                                                ║
║    .venv\Scripts\activate                                    ║
║    .venv\Scripts\pyinstaller.exe AEIA.spec                   ║
║    (output: dist\AEIA.exe)                                   ║
║                                                              ║
║  EDIT RULES (NO RECOMPILE):                                  ║
║    %APPDATA%\AEIA\rules\engineering_rules.json               ║
║                                                              ║
║  EDIT THRESHOLDS (NO RECOMPILE):                             ║
║    %APPDATA%\AEIA\config\settings.json                       ║
║                                                              ║
║  Python Version: 3.10.11                                     ║
║  GUI Framework:  PyQt5 5.15.11                               ║
║  Build Tool:     PyInstaller 6.21.0                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```
