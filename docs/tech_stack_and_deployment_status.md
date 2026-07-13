# AEIA Technical Overview & Deployment Status

This document explains the technical architecture of **AEIA (AI-Powered Engineering Insight
Assistant)**, its current implementation status, and considerations for deploying it on an engineer's
offline machine.

## 1. Technology Stack

The system is built using a **single-process desktop architecture** — no server, no browser, no network:

* **Language:** Python
* **GUI:** PyQt5 (Tkinter reserved as a fallback only if Windows 7 support becomes mandatory)
  * *Why this stack?* PyQt5 gives a native-feeling, responsive desktop window without needing a
    browser or any web technology — appropriate for an offline engineering tool.
* **Data Processing:** Pandas
* **Numerical Computing:** NumPy
* **Statistical Analysis:** SciPy
* **Machine Learning:** Scikit-learn (Isolation Forest for multivariate anomaly detection)
  * *Why this stack?* All three are mature, CPU-only, well-documented libraries with no GPU
    dependency — matching NFR-002.
* **Database:** SQLite
  * *Why this stack?* SQLite is an embedded, file-based database — no server process to install,
    configure, or keep running. Perfect for a single-user offline desktop tool.
* **Visualization (Optional):** Matplotlib
* **Report Generation:** ReportLab
* **NLP (template-based summaries):** NLTK / spaCy
* **Packaging:** PyInstaller (produces a single offline `.exe` — see `packaging_deployment_guide.md`)
* **Configuration:** JSON (`config/settings.json`, `rules/engineering_rules.json`)

---

## 2. Windows 7 Client Compatibility

The project proposal notes Tkinter as a fallback "if Windows 7 support becomes mandatory."

**Will AEIA run on Windows 7?**
* **PyQt5** primarily targets Windows 10/11. Running it reliably on Windows 7 is not guaranteed
  without additional testing, since recent PyQt5/Qt5 builds have been dropping Windows 7 support.
* **If Windows 7 support is confirmed as a hard requirement**, the fallback plan is to build the GUI
  layer with **Tkinter** instead (ships with the Python standard library, has a long history of
  Windows 7 compatibility), while keeping every `core/` and `database/` module unchanged — this is
  exactly why `core/` has zero GUI dependencies (see `code_hygiene_guide.md`).
* This is tracked as future-scope item **FS-007** and is *not* required unless confirmed.

---

## 3. Server Requirements

**Is any server software required?**
* **No.** Unlike a networked document-management system, AEIA has no backend server, no LAN
  dependency, and no separate database server to install. SQLite lives inside a single file
  (`aeia.db`) that the application reads and writes directly.
* The entire application — GUI, analysis engines, and database — runs inside one process on the
  engineer's own PC.

---

## 4. What Is Implemented So Far

**Current phase: Implementation & Testing Complete.** All 12 application modules are coded and the core pipeline is fully validated against ground truth data.

* ✅ Dataset Import (Module 1) — done
* ✅ Data Preprocessing (Module 2) — done
* ✅ Statistical Analysis Engine (Module 3) — done
* ✅ Pattern & Anomaly Detection (Module 4) — done
* ✅ Rule-Based Expert System (Module 5) — done
* ✅ Insight & NL Summary Generation (Module 6) — done
* ✅ Conclusion & Recommendation Engine (Module 7) — done
* ✅ Visualization (Module 8) — done
* ✅ Report Generation (Module 9) — done
* ✅ Main Dashboard / GUI Shell (Module 10) — done
* ✅ Settings & Configuration (Module 11) — done
* ✅ Analysis History / Session Log (Module 12) — done

---

## 5. What Is NOT Implemented (Pending / Future Scope)

Based on the project proposal's Future Scope section, the following are explicitly deferred beyond the
initial version:

1. **Image dataset support** — analyzing scanned charts/images directly (FS-001).
2. **PDF engineering document support** as a direct input format (FS-002).
3. **Optional local LLM integration** for richer narrative generation — deliberately deferred to keep
   the current version fully explainable (XAI), with no generative-model uncertainty (FS-003).
4. **Historical analytics dashboard** — trend visualization across many past sessions, beyond the
   simple History list in Module 12 (FS-004).
5. **Engineering knowledge base** — a browsable, expanded library of domain rules beyond the starter
   rule set (FS-005).
6. **Multi-user support** — only relevant if the tool is later deployed on a shared workstation (FS-006).

---

## Next Steps

With requirements and design documentation complete, the next phase is to scaffold the folder
structure from `technical_design.md`, implement `core/data_loader.py` first (the foundation every
other module depends on), and begin working through the modules in the order listed in Section 4,
validating each against its corresponding test cases in `test_cases.md` as it's built.
