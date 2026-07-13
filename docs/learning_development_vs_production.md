# Learning Guide: Running from Source vs. Running the Packaged App

Welcome! As a beginner learning through building **AEIA (AI-Powered Engineering Insight Assistant)**,
it's completely normal to wonder why you sometimes run `python main.py` in a terminal, and whether
you'll always need to do that.

This guide breaks down the core concepts of **Development Mode** versus **Packaged (Production) Mode**
for a desktop application — which is a bit different from a website, because there's no server to
start and stop.

---

## 🏗️ 1. Development Mode (What we do while building AEIA)

**Development mode** is your workshop. When you're writing code, testing a new detection method, or
fixing a bug, you want instant feedback and full error messages.

### How it works:
- You run the app directly from source:
  ```bash
  python main.py
  ```
- Python reads `main.py`, imports everything from `core/`, `gui/`, and `database/`, and launches the
  PyQt5 window.
- If something crashes, you see the **full Python traceback** in the terminal — exactly which file and
  line caused the problem. This is invaluable while developing, but not something you'd want an
  engineer-user to see.
- You're running inside a **virtual environment** (`venv`) with all the exact package versions from
  `requirements.txt` installed — this keeps your dependencies isolated from other Python projects on
  your machine.

### Why is there only one terminal (unlike a web app)?
AEIA has **no separate backend server** — there's nothing like IODMS's two-terminal
frontend/backend split. It's a single Python process: one terminal, one `python main.py` command, and
the GUI window that opens *is* the whole application.

---

## 🚀 2. Packaged (Production) Mode — The End Goal

**Packaged mode** is the polished, final `.exe` file that an engineer double-clicks from their desktop,
with **no Python installed on their machine at all**.

### How we get there: PyInstaller

Instead of running `python main.py`, we run:
```bash
pyinstaller --onefile --windowed --name AEIA main.py
```

**What happens?** PyInstaller bundles the Python interpreter, every library from `requirements.txt`
(Pandas, NumPy, SciPy, scikit-learn, PyQt5, ReportLab, etc.), and your own `core/`, `gui/`, and
`database/` code into a single `AEIA.exe` file. The engineer's PC never needs Python — everything the
app needs is already inside the `.exe`.

Full packaging steps live in `packaging_deployment_guide.md` — this document is about the *concept*,
that one covers the *commands*.

### What's different in Packaged Mode?

| Aspect | Development Mode | Packaged Mode |
|---|---|---|
| **How you start it** | `python main.py` in a terminal | Double-click `AEIA.exe` (or a Start Menu / desktop shortcut) |
| **Python required on the machine?** | Yes | No — it's bundled inside the `.exe` |
| **Error visibility** | Full traceback in terminal | Friendly error dialog only (FR-084) — tracebacks are logged to a file instead, not shown raw |
| **Startup time** | Fast (interpreter already warm) | Slightly slower on first launch (unpacking bundled files) |
| **Code changes** | Instant — just save and re-run | Requires re-running PyInstaller and re-distributing the `.exe` |
| **Where it runs** | Any machine with Python + the venv set up | Any Windows 10/11 (64-bit) machine, even completely offline |

---

## 🧠 Why There's No "Service" or "Auto-Start" Step

If you've read about server-based systems, you might expect a step where the app is registered as a
Windows Service (like NSSM does for a backend server) so it starts automatically on boot. **AEIA doesn't
need this.** It's a desktop application an engineer opens when they want to analyze a dataset and closes
when they're done — like Excel or Notepad, not like a server that must always be running in the
background. There's no "always-on" requirement in the project proposal, so the app simply launches on
demand.

---

## Your Next Steps in the Learning Journey

For now, keep using **Development Mode** (`python main.py`) to build and test each module — Import,
Preprocessing, Statistics, Anomaly Detection, Rules, Insights, and Report Export. Once the full
workflow (FR-081) works end-to-end and the test cases in `test_cases.md` pass, we'll move to
**Packaged Mode** using the steps in `packaging_deployment_guide.md` to produce the final `AEIA.exe`.
