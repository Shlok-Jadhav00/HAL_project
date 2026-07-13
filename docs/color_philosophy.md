# AEIA Color Philosophy

## Core Design Principle

**"Explainable Engineering Console"**

The interface should communicate:

* Precision
* Trustworthiness
* Calm focus during long analysis sessions
* Clear severity signaling (Info / Warning / Critical)
* Technical, engineering-grade professionalism

Not:

* Consumer app playfulness
* Startup dashboard flash
* Marketing website gradients
* Gaming HUD neon

---

## Emotional Positioning

| Attribute | Visual Feeling |
|---|---|
| Aerospace/Avionics | Precise, disciplined, instrument-panel clarity |
| Offline/Self-contained | Grounded, no external "cloud" cues (no glossy web-service look) |
| Explainable AI | Transparent — findings should look traceable, not mysterious |
| Long analysis sessions | Calm, high-contrast, low eye-strain |

---

## The Palette

**CRITICAL RULE: 7:1 Contrast Ratio.** Engineers may stare at result tables for hours while reviewing
a large dataset — readability is the absolute priority. No low-contrast grey-on-grey.

| Element | Color Name | Hex Code | Why? |
|---|---|---|---|
| **Primary Brand** | Instrument Navy | `#10243E` | Anchors the sidebar and top bar. Reads as precise and authoritative, like a cockpit instrument bezel. |
| **Secondary Accent** | Signal Blue | `#2563EB` | Links, secondary buttons, active tab indicator — brighter than Navy but still restrained. |
| **Background** | Console Grey | `#F7F8FA` | A very subtle, cool grey — not pure white — to reduce glare during long review sessions. |
| **Card / Panel** | Panel White | `#FFFFFF` | Tables and forms sit on this to stand out against Console Grey. |
| **Borders / Lines** | Steel Line | `#D3D8E0` | Clean division between cells and sections without harsh black rules. |
| **Text Primary** | Graphite | `#111827` | Never pure `#000000`. Softer on the eyes, still high-contrast. |
| **Text Secondary** | Muted Slate | `#6B7280` | Helper text, timestamps, minor labels. |
| **Critical** | Alert Red | `#DC2626` | Reserved strictly for Critical-severity findings and destructive actions (e.g. delete session). |
| **Warning** | Caution Amber | `#D97706` | Warning-severity findings and non-destructive alerts. |
| **Info / Nominal** | Signal Blue (light tint) | `#DBEAFE` (bg) / `#1D4ED8` (text) | Info-severity findings — present, but visually quiet. |
| **Success / Nominal Result** | Confirmed Green | `#16A34A` | "No significant findings," successful export, completed session. |

---

## Severity Color Mapping (the most important rule in this document)

Because AEIA's entire value proposition is **explainable, trustworthy findings**, color must never be
decorative when it touches a Finding, Anomaly, or Recommendation. The three severity levels defined in
`AEIA_requirements_context.md` (FR-038) map to exactly one color each, used consistently everywhere —
result tables, chart highlight markers, report PDF badges, and History list icons:

| Severity | Color | Used For |
|---|---|---|
| **Critical** | Alert Red `#DC2626` | Rule matches or anomalies requiring immediate engineering attention |
| **Warning** | Caution Amber `#D97706` | Anomalies/patterns worth reviewing but not urgent |
| **Info** | Signal Blue tint `#DBEAFE` / `#1D4ED8` | Background context findings, no action implied |

**Never** use Alert Red for ordinary UI chrome (buttons, headers, borders) — if red appears anywhere in
the interface, it must mean "Critical," with no exceptions. This is what lets an engineer scan a report
in seconds and know exactly where to look first.

---

## Module Color Identifiers

Each major workflow step gets a subtle color identity, applied as a top-border accent on its main panel
or its header text — this helps an engineer instantly recognize which stage of the workflow they're in.

| Module | Identifier Color | Hex | Rationale |
|---|---|---|---|
| **Import** | Signal Blue | `#2563EB` | The neutral, welcoming entry point. |
| **Preprocess** | Teal | `#0D9488` | Denotes "cleaning in progress," distinct from raw import. |
| **Statistics** | Instrument Navy | `#10243E` | The core, most "official" analysis output. |
| **Anomaly & Pattern Detection** | Deep Indigo | `#4338CA` | Distinct from plain statistics — signals "something was found here." |
| **Rules / Expert System** | Slate Purple | `#6D28D9` | Marks reasoning-layer output, separate from raw detection. |
| **Findings & Conclusion** | Graphite | `#111827` | Neutral, text-forward — the severity colors do the work here, not the module color. |
| **Report Export** | Confirmed Green | `#16A34A` | Signals completion and successful output. |
| **History** | Muted Slate | `#6B7280` | A quiet, archival utility color. |
| **Settings** | Warm Brown | `#7C4A1E` | Very distinct — if you see brown, you know you're changing thresholds or rules, not viewing results. |

---

## Specific UI Component Rules

1. **The Sidebar:**
   * **Background:** Instrument Navy (`#10243E`).
   * **Text:** White (`#FFFFFF`).
   * **Active Item:** A subtle lighter navy or white semi-transparent overlay (`rgba(255,255,255,0.12)`)
     — never a bright neon highlight.

2. **Result Tables (Statistics, Anomalies, Rule Matches):**
   * **Header Row:** Instrument Navy background, white text.
   * **Rows:** Pure white with Steel Line borders; zebra striping is optional and should stay very subtle.
   * **Row Hover:** Very light blue tint (`#EFF6FF`).
   * **Severity Column:** Always rendered as a small colored badge/chip using the Severity Color Mapping
     above — never as plain text color alone (colorblind-safe: pair color with an icon/label).

3. **Forms (Settings, Rule Editor):**
   * Clean white cards with Steel Line borders.
   * On focus, border changes to Signal Blue with a slight glow.

4. **Charts (Trend, Histogram, Correlation Heatmap):**
   * Base chart lines/bars in Instrument Navy or Signal Blue.
   * Anomaly markers on trend charts always in Alert Red, regardless of the base chart color, so they
     pop immediately against the data line.

5. **Report PDF:**
   * Section headers in Instrument Navy.
   * Severity badges next to each finding, matching the on-screen severity colors exactly, so the
     printed report and the live app never disagree about what's Critical.
