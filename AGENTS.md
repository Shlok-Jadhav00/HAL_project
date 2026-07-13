# AGENTS.md — AEIA (AI-Powered Engineering Insight Assistant)

## What AEIA is
An offline, single-user PyQt5 desktop app for avionics/aerospace engineers. It imports CSV/XLSX/JSON/TXT/LOG
datasets, runs statistical analysis + anomaly detection + a rule-based expert system, and exports a PDF report
with plain-language findings and recommendations. It is Explainable AI by design: statistics, thresholds, and
rules only — no generative LLM, no cloud calls, no GPU. It must run fully offline on CPU-only hardware.

## Current status
Requirements and design are complete and locked (see `docs/changelog.md`). No application code exists yet.
You are building this from scratch, module by module.

## Read before writing any code, in this order
1. `docs/AEIA_requirements_context.md` — 105 FRs, 12 NFRs, 5 EIRs across 12 modules. Defines *what* to build.
2. `docs/hld.md` and `docs/technical_design.md` — architecture, the 11-table SQLite schema, and the exact
   folder/file layout. Defines *how it's structured*. Follow this folder structure exactly; don't improvise
   a different one.
3. `docs/implementation_specification.md` — every concrete constant, formula, JSON schema, NLG template, and
   error message the requirements leave implicit. This is *the exact values* — nothing here should be
   guessed. Its §10 "Cross-Reference Index" tells you exactly which section to read before writing any given
   file.
4. `sample_data/README.md` — ground-truth expected statistics, anomalies, correlations, and rule firings for
   `sample_data/engine_test_run.csv`. Validate each module's output against these real numbers as you build
   it, not just against the requirement text.

`AEIA_requirements_context.md`, `technical_design.md`, and `implementation_specification.md` together are the
complete, authoritative source of truth for this project — there is no separate external proposal document to
consult.

## Hard constraints — apply to every change, no exceptions
- 100% offline, CPU-only, always. No network calls anywhere in the app, no GPU dependency.
- `core/` and `database/` must have **zero PyQt5 imports** — GUI, logic, and data access stay strictly
  separated (`docs/code_hygiene_guide.md`). `gui/` never runs raw SQL directly.
- No hard-coded thresholds, paths, or magic numbers. Everything tunable lives in `config/settings.json` or
  `rules/engineering_rules.json`.
- No generative-LLM reasoning inside AEIA itself — insight/summary text is template-based only (FR-055), to
  keep the app fully explainable (NFR-006). This restricts what the *application* does, not you as the coding
  agent.
- Every non-trivial function's comment references the FR ID it implements (`docs/code_hygiene_guide.md`
  Rule 1) — this is how `test_cases.md` stays traceable to real code.
- UI colors come only from the palette in `docs/color_philosophy.md`, applied via `gui/theme.py` — never
  inline hex codes in panel files.
- `config/settings.json`, `rules/engineering_rules.json`, and `database/schema.sql` already exist at their
  correct target paths in this workspace — extend them as needed, don't regenerate or restructure them.

## If something is genuinely unspecified
`implementation_specification.md` exists precisely so you don't have to guess. If you hit a value, behavior,
or format that truly isn't pinned down anywhere in `docs/`, stop and ask Shlok rather than inventing one
silently — a guessed default in one module contradicting a different guessed default in another is exactly
the failure mode this documentation set was built to prevent.

## Build order
Per `docs/tech_stack_and_deployment_status.md` ("Next Steps"): scaffold the folder structure from
`docs/technical_design.md` Part B first, then `core/data_loader.py` (Module 1 — every other module depends on
it), then the remaining modules in the order listed in `docs/AEIA_requirements_context.md`. Validate each
module against its cases in `docs/test_cases.md` before moving to the next. Use Planning Mode for the initial
scaffold and for each new module — this project is precise enough that the plan is worth reviewing before
code gets written.

## Keep the living documents current as you work
- Add an entry to `docs/changelog.md` (template at its bottom) for each completed module or notable decision.
- Add a real entry to `docs/teaching_code_changes.md` whenever you hit and fix an actual bug, in its exact
  format — only real bugs, never invented ones, per the file's own warning.
- Flip the status checkboxes in `docs/tech_stack_and_deployment_status.md` (§4) as modules move from
  not-started to done.

## Packaging (later phase, not now)
Don't run PyInstaller or worry about `.exe` packaging until every module passes its test cases. When that
phase starts, follow `docs/packaging_deployment_guide.md` exactly.
