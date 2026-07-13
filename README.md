# AEIA — AI-Powered Engineering Insight Assistant

Offline PyQt5 desktop app for engineering data analysis. Requirements and design are complete;
implementation hasn't started (see `docs/changelog.md` for the full status).

## Start here
- **`docs/`** — the full specification: requirements, architecture, exact implementation values, code/UI
  standards, and test cases. `docs/changelog.md` is a one-page map of every document and why it exists.
- **`AGENTS.md`** — instructions for whichever coding agent (Antigravity, etc.) implements this project.
  It doesn't repeat what's already in `docs/`; it just points to reading order and non-negotiable rules.
- **`sample_data/`** — a small deterministic dataset with pre-computed ground-truth results, for
  validating the implementation as it's built.
- **`config/`, `rules/`, `database/schema.sql`, `requirements.txt`** — ready-to-use seed files, already
  placed at the exact paths `docs/technical_design.md` expects. Nothing here needs to be regenerated.

## Note on the original proposal document
`docs/AEIA_requirements_context.md` references a source file,
`AI-Powered_Engineering_Insight_Assistant_Project_Proposal.docx`. That file isn't included in this
package — `docs/` was written to be a self-contained, authoritative replacement for it. If you want the
original on hand for historical reference, add it under a new `source/` folder; nothing in `docs/` or
`AGENTS.md` depends on it being present.

## Building this with Google Antigravity
1. Open this `AEIA/` folder as a Workspace (or clone/copy it into wherever your Antigravity workspaces
   live).
2. Start a new conversation and use **Planning Mode** for the first prompt, e.g.: *"Scaffold the project
   per docs/technical_design.md and implement core/data_loader.py first."* Review the plan before you
   approve it — `AGENTS.md` already points the agent at the right reading order.
3. Stay on **Review-driven development** autonomy (the default) rather than full agent-driven autonomy,
   at least until the core analysis engines are in place. The spec is precise enough that it's worth
   checking each module's plan and diff against `docs/implementation_specification.md` before it lands.
4. Validate early modules against `sample_data/engine_test_run.csv` + `sample_data/README.md` — real
   numbers, not just "looks plausible."
5. `core/`, `gui/`, `database/*.py`, and `tests/` are intentionally not scaffolded yet — that's the
   agent's first task, per `AGENTS.md`, so you get a chance to review the plan before any code exists.
