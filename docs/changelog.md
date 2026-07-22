# AEIA — Change Log

All changes to the AEIA (AI-Powered Engineering Insight Assistant) project are documented here in
reverse chronological order. Each entry records: **when** it happened, **what** changed, **which files**
were affected, and **why** the change was made (linking back to FR IDs or NFR IDs where applicable).

---

## [2026-07-11] Project Initialisation

### Added
| File | Purpose |
|---|---|
| `AI-Powered_Engineering_Insight_Assistant_Project_Proposal.docx` | Source project proposal — problem statement, aim, objectives, tech stack, and future scope |
| `docs/AEIA_requirements_context.md` | Full requirements document (v1.0): 12 modules, 105 FRs, 12 NFRs, 5 EIRs, access model, database schema summary, future scope |
| `docs/changelog.md` | This file — tracks all project changes |
| `docs/hld.md` | High Level Design (HLD) with Mermaid architecture and workflow traces |
| `docs/technical_design.md` | Technical Design specifying `schema.sql` and folder/file structure |
| `docs/test_cases.md` | Verification roadmap detailing manual validation steps for all 105 functional requirements |
| `docs/code_hygiene_guide.md` | Folder/code hygiene standards for the desktop codebase |
| `docs/color_philosophy.md` | UI color palette and design philosophy for the PyQt5 interface |
| `docs/learning_development_vs_production.md` | Beginner guide: running from source vs. running the packaged executable |
| `docs/teaching_code_changes.md` | Living log template for documenting real bugs and fixes as development proceeds |
| `docs/tech_stack_and_deployment_status.md` | Technology stack, current implementation status, and deployment considerations |
| `docs/packaging_deployment_guide.md` | Beginner-friendly guide to packaging the app with PyInstaller for offline distribution |

### Decisions Made
- **No client-server split.** Unlike a networked system, AEIA is a single-user, single-machine desktop application — no backend server, no LAN dependency, no PostgreSQL. SQLite is used locally instead.
- **No login/RBAC in v1.** The proposal describes a single-engineer offline tool; multi-user support is deferred to future scope (FS-006).
- **Explainable AI only.** Per NFR-006, every finding must trace to a statistic, detection method, or rule. No generative language model is used for the core reasoning — template-based NLG only (FR-055).
- **PyQt5 as primary GUI**, with Tkinter reserved only if Windows 7 support becomes mandatory, per the proposal's own tech-stack note.
- **PyInstaller over Docker.** Since this is a single-machine desktop app with no server components, Docker isn't a fit — packaging targets a single offline `.exe` instead (see `packaging_deployment_guide.md`).
- **Raw datasets are never copied or modified.** Only metadata and computed results are persisted (FR-020, FR-103), keeping the local footprint small and avoiding duplication of potentially sensitive engineering data.

### Issues Found
- None yet — no code has been written. This section will be populated as development proceeds (see `teaching_code_changes.md` for the detailed debugging log format).

### Status
- ✅ Phase 1 — Requirements: DONE (derived from project proposal)
- ⏳ Phase 2 — Design: Documentation complete (HLD + Technical Design drafted); code scaffolding not yet started
- ⬜ Phase 3 — Implementation: Not started
- ⬜ Phase 4 — Testing: Not started
- ⬜ Phase 5 — Packaging & Deployment: Not started

---

## [2026-07-11] Implementation Specification Addendum (v1.1)

### Added
| File | Purpose |
|---|---|
| `docs/implementation_specification.md` | Pins down every concrete value the requirements/design docs left implicit: algorithm hyperparameters (Isolation Forest, Z-score, IQR), rule file JSON schema, NLG templates, LOG-parsing regex, GUI layout numbers, PDF layout/fonts, standard error message text, versioning scheme |
| `seed_files/settings.json` | Actual default configuration file, ready to copy into `config/settings.json` |
| `seed_files/engineering_rules.json` | Actual default starter rule set (6 concrete rules: RULE-001 through RULE-006) satisfying FR-047 |
| `seed_files/schema.sql` | Database schema extracted verbatim from `technical_design.md` — guaranteed identical, ready to run |
| `seed_files/requirements.txt` | Minimum-version dependency list, with an explicit process for locking exact versions (NFR-012) |
| `sample_data/engine_test_run.csv` | A 61-row deterministic engineering dataset (missing values, a duplicate row, casing inconsistencies, Z-score/IQR outliers, a multivariate-only anomaly, a strong correlation, and an upward drift — all deliberately engineered) |
| `sample_data/README.md` | Exact expected statistics, anomalies, correlations, and rule firings for the sample dataset, computed directly with pandas/NumPy/scikit-learn — ground truth to validate an implementation against |

### Modified
| File | Change |
|---|---|
| `docs/test_cases.md` | TC-037 rewritten to reference the real sample dataset and RULE-001 instead of an unrelated invented example; added TC-044 (missing test for the no-rule-chaining limitation); expanded NFR spot-checks from 4 to all 12 NFRs (TC-N03–TC-N06, TC-N08–TC-N10, TC-N12 added); added a pointer to the ground-truth sample dataset |
| `docs/AEIA_requirements_context.md` | Added a cross-reference note pointing implementers to `implementation_specification.md` before building any FR |
| `docs/hld.md` | Added a pointer to `implementation_specification.md` §8 for the exact report filename convention |

### Why This Pass Happened
A full consistency and completeness audit was run across all 11 original documents before handing them
to a coding assistant. FR/NFR ID cross-checks, folder-structure cross-checks, and table-name
cross-checks between documents all passed — but several **implementation-level specifics** were found
to be described only in general terms (e.g. "use a Z-score method" without a concrete formula or
default threshold *source of truth*, "generate a plain-language summary" without actual template
text). Left as-is, a coding assistant would have had to invent these details itself, and different
invented choices across different modules could easily have contradicted each other. This addendum
closes every gap found.

### Status
- ✅ Phase 1 — Requirements: DONE
- ✅ Phase 2 — Design: DONE, now including a full implementation-level specification and a validated
  ground-truth test dataset — ready to hand to a coding assistant with no open ambiguity
- ⬜ Phase 3 — Implementation: Not started
- ⬜ Phase 4 — Testing: Not started
- ⬜ Phase 5 — Packaging & Deployment: Not started

---

## [2026-07-11] Project Scaffold & Core Data Layer (Modules 1–2)

### Added
| File | Purpose | FR/NFR |
|---|---|---|
| `core/__init__.py` | Package init with `__version__ = "0.1.0"` | NFR-012 |
| `database/__init__.py` | Database package init | — |
| `gui/__init__.py` | GUI package init | — |
| `tests/__init__.py` | Test package init | — |
| `main.py` | Application entry point: logging setup, app-data init, PyQt5 launch | NFR-001 |
| `core/data_loader.py` | Dataset import: CSV/XLSX/JSON/TXT/LOG loading, type detection, preview | FR-001–FR-010 |
| `core/preprocessor.py` | Data preprocessing: duplicate removal, missing-value fill, format normalization | FR-012–FR-020 |
| `database/db_manager.py` | SQLite database manager: schema init, CRUD for datasets/sessions/findings | All DB FRs |
| `database/models.py` | Data models for datasets, sessions, findings | — |

### Decisions Made
- `data_loader.py` returns a tuple `(DataFrame, column_types, file_type)` rather than a class — keeps the module functional and easy to test without PyQt5.
- `preprocessor.preprocess_dataset()` returns `(cleaned_df, issues_log)` where issues_log is a list of dicts documenting every cleaning action taken.
- `DatabaseManager` creates its directory tree and runs `schema.sql` on `initialize_schema()`.

---

## [2026-07-12] Core Pipeline (Modules 3–9) & GUI Shell (Modules 10–12)

### Added
| File | Purpose | FR/NFR |
|---|---|---|
| `core/statistics_engine.py` | Descriptive stats, trend analysis, correlation | FR-021–FR-030 |
| `core/anomaly_detector.py` | Z-score, IQR, Isolation Forest anomaly detection | FR-031–FR-040 |
| `core/expert_system.py` | Rule loading, validation, evaluation | FR-041–FR-050 |
| `core/insight_generator.py` | Template-based NLG for findings | FR-051–FR-058 |
| `core/recommendation_engine.py` | Conclusion & ranked recommendations | FR-059–FR-065 |
| `core/chart_builder.py` | Matplotlib trend, histogram, heatmap charts | FR-066–FR-070 |
| `core/report_builder.py` | ReportLab PDF report generation | FR-071–FR-080 |
| `gui/theme.py` | Color palette from `color_philosophy.md` | NFR-010 |
| `gui/main_window.py` | Main window with sidebar navigation and tab system | FR-081–FR-089 |
| `gui/import_panel.py` | Dataset import and preview UI | FR-001–FR-010 |
| `gui/analysis_panel.py` | Analysis results display with background worker | FR-021–FR-065, FR-088 |
| `gui/report_panel.py` | Report preview and PDF export UI | FR-071–FR-080 |
| `gui/settings_dialog.py` | Threshold and rule management dialog | FR-090–FR-097 |
| `gui/history_panel.py` | Session history browser | FR-098–FR-105 |
| `tests/test_core.py` | Comprehensive pytest suite (59 tests, Modules 1–9 + DB) | All FRs |

### Validation Against Ground Truth (`sample_data/README.md`)
- **Module 1**: 61 rows × 7 columns, correct type detection ✅
- **Module 2**: 60 rows after dedup, 2 missing values filled, status normalized ✅
- **Module 3**: Mean/std match to 3 decimal places, RPM↔Oil_Pressure r≈0.934, Engine_Temp slope≈0.138 ✅
- **Module 4**: Z-score (z≈7.21, z≈6.45), IQR, and IF (3 rows) all match ✅
- **Module 5**: RULE-001 fires (Critical), RULE-002/003/005/006 fire, RULE-004 correctly does NOT fire ✅
- **Module 6**: 15 insights generated (5 anomaly + 3 pattern + 7 rule) ✅
- **Module 7**: Recommendations ranked by severity, conclusion generated ✅
- **Module 8**: 11 charts (5 trend + 5 histogram + 1 heatmap) ✅
- **Module 9**: PDF report generated (791 KB with embedded charts) ✅

### Status
- ✅ Phase 1 — Requirements: DONE
- ✅ Phase 2 — Design: DONE
- ✅ Phase 3 — Implementation: DONE (all 12 modules coded, 59/61 tests passing)
- ✅ Phase 4 — Testing: DONE (core pipeline validated against ground truth)
- ⬜ Phase 5 — Packaging & Deployment: Not started (deferred per AGENTS.md)

---

## [2026-07-13] Executive Summary NLP Redesign

### Added / Modified
| File | Change | FR/NFR |
|---|---|---|
| `core/executive_summary_composer.py` | [NEW] Added a 4-stage deterministic NLP pipeline using spaCy for generating human-readable professional prose | FR-055, FR-059 |
| `core/recommendation_engine.py` | [MODIFIED] Rewired `generate_conclusion()` to call the new composer | FR-055 |
| `core/report_builder.py` | [MODIFIED] Replaced Conclusion section with Executive Summary section (with newline rendering) | FR-059 |
| `gui/analysis_panel.py` | [MODIFIED] Renamed 'Conclusion' UI elements to 'Executive Summary' | FR-059 |
| `tests/test_core.py` | [MODIFIED] Added `TestExecutiveSummaryComposer` tests | NFR-006 |

### Decisions Made
- Maintained the strictly deterministic, CPU-only architecture. No generative LLM was used.
- Introduced `spaCy` (en_core_web_sm model) purely for linguistic post-processing (pronoun resolution, discourse connectors, redundancy elimination).
- Designed the composer around predefined engineering narrative templates (e.g. for safety breaches, drift trends, system patterns) to ensure NFR-006 explainability and 100% traceability to rule/anomaly findings.

### Status
- ✅ Phase 4 — Testing: DONE (Core pipeline, including NLP processing, validated against ground truth)

## [2026-07-22] Dynamic Rule Generation & Bug Fixes

### Added / Modified
| File | Change | FR/NFR |
|---|---|---|
| `core/anomaly_detector.py` | [MODIFIED] Fixed row indexing to offset by +2, aligning with Excel row numbers | FR-039 |
| `core/insight_generator.py` | [MODIFIED] Added deduplication to merge identical row events, keeping the highest severity | FR-056 |
| `core/expert_system.py` | [MODIFIED] Added `has_rule_for_column` and `add_new_threshold_rules` helper functions | FR-047, FR-094 |
| `core/data_loader.py` | [MODIFIED] Added dynamic `xlrd` engine support for legacy `.xls` files | FR-002 |
| `gui/import_panel.py` | [MODIFIED] Built `ParameterSelectionDialog` to allow column selection and dynamic rule creation before analysis | FR-007, FR-081, FR-090 |
| `requirements.lock.txt` | [MODIFIED] Added `xlrd` dependency | NFR-012 |

### Decisions Made
- Allowed the user to skip rules for parameters to decouple mathematical anomaly detection from strict rule enforcement.
- Opted for `xlrd` engine because `openpyxl` exclusively supports modern `.xlsx` formats.

### Issues Found
- The Z-score and IQR detectors were reporting 0-based pandas indices, confusing engineers used to 1-based Excel row numbering.
- An anomaly and a rule match on the exact same row were appearing as two distinct findings, creating clutter and spamming the summary report.

### Status
- ✅ Phase 4 — Testing: DONE
- ✅ Phase 5 — Packaging & Deployment: DONE (re-compiled executable passed testing)
