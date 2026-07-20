# AEIA — Design Philosophy (v1.1)

> **Scope:** This document defines design intent and visual language for the AEIA desktop application.
> It does not override requirements — where a conflict exists between this document and
> `AEIA_requirements_context.md`, the requirements document wins and this one must be updated.
> **For exact hex values, colour token names, and severity colour mapping, see `docs/color_philosophy.md`
> — this document describes intent, that document decides implementation.**

---

## Vision Statement

AEIA should feel like a professional engineering decision-support tool: calm, precise, fast, and
trustworthy. The interface must help engineers understand the system quickly, not distract them with
decoration.

---

## Product Identity

AEIA is not a consumer app and not a generic dashboard. It is a technical desktop application for
engineering analysis in offline environments. The design should communicate:

- reliability
- control
- clarity
- traceability
- low visual noise
- operational seriousness

---

## Design Principles

### 1. Clarity First
Every screen must make the next action obvious. The five-step workflow — **Import → Preprocess →
Analyze → Review Findings → Export Report** — should always be visually legible at a glance (FR-081).

### 2. Information Density With Breathing Space
AEIA should display a lot of information, but never feel crowded. Use structured spacing, grouped
cards, and clear hierarchy.

### 3. Status Over Decoration
Colour communicates status, severity, or action. It is never used purely for aesthetics. If removing
a colour from an element changes nothing about its meaning, the colour should not be there.

### 4. Quiet Motion
Transitions should be subtle and purposeful. Motion is for feedback, not entertainment.

### 5. Engineering Readability
The interface must remain legible on low-end workstations and under time pressure. Text, charts, and
tables should be readable at a glance, not requiring close inspection.

### 6. Explainability Visible in the UI
The UI must reinforce how findings were produced. Every critical result must have a visible path back
to its source — the statistic, the detection method, or the rule ID that produced it. This is not a
style preference; it is a direct product requirement (NFR-006). If a finding appears without a
traceable source label, the screen is incomplete.

### 7. Desktop-First, Offline-First
The design should feel native to a Windows engineering workstation — not like a web page forced into
a desktop shell. No browser-style navigation patterns, no cloud iconography, no loading spinners that
imply a network round-trip.

---

## Layout Philosophy

### App Structure

```
┌─────────────────────────────────────────────────────────┐
│  Top App Bar — dataset name · row count · last run time │  ← FR-086
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │         Central Workspace                   │
│ 220px    │  (analysis results, findings, charts)       │
│          │                                             │
│ Import   │                                             │
│ Analysis │                                             │
│ History  │                                             │
│ Settings │                                             │
│          │  ┌─────────────────────────────────────┐   │
│          │  │  Detail / action panel (lower area) │   │
│          │  └─────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────┘
```

- Sidebar: 220px expanded, 60px icon-only collapsed (FR-082, `docs/implementation_specification.md` §7)
- Top app bar: persistent; shows current dataset name, row count, and last analysis timestamp
- Central workspace: tabbed — one tab per open dataset session (FR-085)

### Screen Flow (canonical — reconciles FR-081 with the UI steps below)

The five required workflow stages map to the following UI screens:

| Stage (FR-081) | UI Screen(s) |
|---|---|
| 1. Import | Import Panel — file browse / drag-drop, format confirmation, column selection |
| 2. Preprocess | Import Panel (continued) — missing-value strategy, duplicate removal, format normalization |
| 3. Analyze | Analysis Panel — progress, then Statistics results tab; Anomalies tab; Patterns tab |
| 4. Review Findings | Analysis Panel — Findings tab (insights, conclusion, recommendations); Charts tab (optional) |
| 5. Export Report | Report Panel — on-screen preview, notes/annotations editor, PDF export |

**History** (FR-098–FR-105) is a separate sidebar destination, not a step in the workflow — an
engineer browses it independently, not as part of an active analysis.

---

## Colour Philosophy

> **Implementation rule:** use only the named tokens from `docs/color_philosophy.md`. Do not
> introduce new hex codes in panel or widget files. All colour references go through `gui/theme.py`.

### Conceptual intent (exact tokens in `color_philosophy.md`)

| Intent | Concept |
|---|---|
| Primary brand / sidebar | Deep navy — authoritative, instrument-panel feel |
| Primary actions / links | Signal blue |
| Background | Very slightly cool grey — reduces glare on long sessions |
| Cards / tables | Pure white against the grey background |
| Borders | Soft steel line |
| Body text | Near-black graphite (never pure black) |
| **Critical findings** | Red — reserved exclusively for Critical severity and destructive actions |
| **Warning findings** | Amber |
| **Info findings** | Blue tint |
| Successful / nominal | Green |

### The non-negotiable severity rule
Red means Critical. Everywhere. Always. An engineer who sees red anywhere in this application will
look for a critical finding. If there is not one, the UI has lied to them. This rule has no
exceptions — not for error dialogs, not for delete buttons styled carelessly, not for any decorative
purpose.

---

## Typography

### Typeface preference (Windows-native, no download required)
1. **Segoe UI** (primary — ships with Windows 10/11)
2. Inter or IBM Plex Sans (fallback if Segoe UI is unavailable)

### Size and weight hierarchy (`docs/implementation_specification.md` §7)

| Element | Size | Weight |
|---|---|---|
| Page / panel title | 18 pt | Bold |
| Section heading | 14 pt | Bold |
| Card title | 12 pt | SemiBold |
| Body text | 10 pt | Regular |
| Secondary / muted text | 9 pt | Regular |
| Table cell | 10 pt | Regular |
| Caption / label | 9 pt | Regular |

### Readability rules
- No font size below 9 pt anywhere
- No all-caps for long labels (short status badges only)
- Table rows: enough line height to read without leaning in
- Summary panels: scannable in under 5 seconds

---

## Spacing and Density

### Spacing rules

| Context | Rule |
|---|---|
| Small controls (buttons, inputs) | Compact but not cramped — 4–6 px internal padding |
| Cards | Generous internal padding — 16–20 px |
| Section separation | Clear visual gap — 24 px minimum between major sections |
| Table rows | Comfortable row height — 32–36 px |
| Dialogs | Enough whitespace to feel intentional — never a wall of controls |

### Density goal
Dense enough for engineering work, but not so dense that it becomes fatiguing over a long review
session. The interface should reward scanning, not require it.

---

## Component Specifications

### Sidebar (FR-082)
- Icon + text label navigation
- Active item clearly distinguished (background highlight, not colour alone)
- Four fixed items in order: **Import · Analysis · History · Settings**
- Collapsible to icon-only mode (60px)
- No sub-menus in v1

### Top App Bar (FR-086)
Persistent. Displays:
- Current dataset filename
- Row count
- Last analysis timestamp
- Application version (small, right-aligned)

### Session Dashboard Cards
Displayed at the top of the Analysis Panel immediately after analysis completes. Six cards:

| Card | Maps to |
|---|---|
| Dataset summary (filename, rows, columns) | FR-051, FR-086 |
| Critical findings count | FR-038, FR-061 |
| Warning findings count | FR-038, FR-061 |
| Info findings count | FR-038 |
| Analysis duration | FR-083 (timing feedback) |
| Report status (Not exported / Exported) | FR-071 |

Card count badge colours follow the severity colour mapping exactly (red / amber / blue tint / green
for 0 findings). A Critical count of zero is shown in green, not grey — green means "clean," which is
meaningful.

### Results Tables (FR-030, FR-035)
- Sortable columns
- Sticky header row
- Zebra striping optional (very subtle if used)
- Severity column: coloured badge/chip + text label (never colour alone — accessibility, FR-related
  to NFR-006)
- Row hover: very light blue tint
- No horizontal scroll on the standard findings table — columns must fit the minimum window width
  (1280px, per `docs/implementation_specification.md` §7)

### Charts (FR-066–FR-070)
Charts are evidence, not decoration.

- Base chart lines/bars: Instrument Navy or Signal Blue
- Anomaly markers on trend charts: always Alert Red, regardless of the base colour
- Axis labels and gridlines: understated (Muted Slate)
- No chart title font larger than 12pt — the section heading above the chart carries the label
- Toggle: charts can be excluded from the report per FR-069; the toggle must be visible on the
  Report Panel before export, not buried in Settings

### Dialogs
- Clear title (what is happening)
- One concise sentence of explanation (why)
- Maximum two action buttons: primary action + cancel
- No decorative iconography that doesn't add meaning
- Destructive actions (e.g. delete session — FR-102): primary button in Alert Red; confirmation
  required before execution

### Settings Panel (FR-091–FR-097)
Settings are grouped by the functional area they affect. Only groups backed by current FRs are
implemented in v1:

| Group | Contents | FRs |
|---|---|---|
| Analysis | Z-score threshold, IQR multiplier, Isolation Forest contamination, correlation threshold | FR-091, FR-094 |
| Rules | Rule list, enable/disable toggle, add/edit rule | FR-092, FR-045 |
| Reports | Default report save folder, include charts by default | FR-093, FR-069 |

> **Future scope (FS):** Performance, Appearance, and Storage settings panels are noted as possible
> future additions but have no current FR coverage and must not be built in v1.

---

## Motion Rules

### Use motion for
- Hover feedback on buttons and table rows (instant, no delay)
- Selection feedback (immediate highlight)
- Progress indication during analysis (FR-083 — spinner or progress bar)
- Subtle view transitions (keep under 150ms)

### Do not use motion for
- Decorative entrance animations
- Bouncing or elastic effects
- Any transition over 200ms that doesn't convey loading state
- Anything that makes the app feel slower than it is

---

## Accessibility Rules

- Maintain strong contrast — body text must meet WCAG AA minimum (4.5:1) against its background
- Never rely on colour alone to communicate status — always pair colour with a text label or icon
- Keyboard navigation: all primary actions reachable by keyboard (FR-087 covers Import and Export
  shortcuts; all other panels must be Tab-navigable)
- Hit targets: minimum 32×32px for any clickable control
- No washed-out grey text for anything the engineer needs to act on

---

## Performance-Aware Design

AEIA runs on older engineering workstations. The UI must look polished without being heavy.

Avoid:
- Large drop shadows on more than one or two surfaces
- Nested panels more than two levels deep
- Transparency or blur effects (slow on integrated graphics)
- More than one animation running at a time
- Icon sets that load from disk at runtime

Prefer:
- Flat cards with a single subtle border
- Crisp, vector-style icons (SVG or Qt's built-in icon set)
- Layout that renders immediately on window open, with data populating progressively

---

## Recommended Visual Personality

AEIA should feel like:
- a premium engineering workstation tool
- a calm analysis console
- a trustworthy industrial instrument
- a serious decision-support system

It should not feel like:
- a consumer web app in a desktop wrapper
- a student assignment
- a flashy sales dashboard
- a generic admin panel template

---

## Reference Inspirations

These systems share the design values AEIA is targeting. Study them for tone and structure, not
for component copying:

- **Microsoft Fluent Design System** — depth, layering, and controlled motion used to communicate
  hierarchy rather than decoration. Documentation at [learn.microsoft.com/fluent-ui](https://learn.microsoft.com/en-us/fluent-ui/)
- **Metro / Modern UI (Windows 8–10 era)** — typography-first layout, icon simplicity, and the
  principle of "content before chrome." Still the clearest articulation of flat-but-readable desktop UI.
- **Qt Style Sheets** — the actual implementation surface. Qt widgets are fully customisable via
  QSS; `gui/theme.py` is where all QSS constants are defined.
- **Material Design 3** — card-based layout, grid discipline, and colour-role thinking (not the
  specific palette, which is too consumer-friendly for AEIA's tone).

---

## Implementation Order

When the UI build begins, follow this sequence to avoid rebuilding foundational elements:

1. Define all design tokens in `gui/theme.py` (colour, font sizes, spacing constants) — nothing
   else is built until this file exists
2. Build the sidebar and top app bar shell (`gui/main_window.py`)
3. Build the Import Panel (`gui/import_panel.py`)
4. Build the Analysis Panel — statistics/anomaly/findings tabs (`gui/analysis_panel.py`)
5. Build the Report Panel — preview and export (`gui/report_panel.py`)
6. Build Settings and History panels
7. Only then: polish spacing, shadows, and hover states across all panels

Do not polish a panel before the one beneath it in the pipeline is working — a beautiful import
screen over a broken analysis engine is misleading, not an improvement.

---

## Non-Negotiables

- Do not sacrifice readability for style
- Do not hide evidence — every finding must show its source
- Do not use animation to distract from slow performance
- Do not use colour without meaning — especially do not use red for anything that is not Critical
- Do not make the UI look or behave like a consumer web app
- Do not break the offline desktop workflow — no element should imply a network connection exists

---

## Final Principle

**AEIA should make the engineer feel more confident after using it than before.**

That confidence comes from clarity, not complexity. From evidence, not assertion. From a tool that
shows its working rather than hiding it.

---

*Document version: 1.1 | Supersedes: AEIA_Design_Philosophy_v1.0*
*Changes from v1.0: fixed broken citation tokens, reconciled screen flow with FR-081, aligned
settings groups with existing FRs (v1 scope only), added colour token cross-reference to
`color_philosophy.md`, mapped dashboard cards to FR IDs, added implementation order section.*
