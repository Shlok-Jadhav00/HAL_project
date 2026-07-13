# Sample Dataset: `engine_test_run.csv`

This is a small, deterministic dataset built specifically for validating an AEIA implementation against
**real, pre-computed expected results** — so a coding assistant (or a human tester) can check its work
against actual numbers instead of guessing whether an implementation is "roughly right."

All figures below were computed directly from the file using pandas / NumPy / scikit-learn with the
exact parameters specified in `docs/implementation_specification.md` — they are not estimates.

**61 rows, 7 columns:** `Sample_ID`, `Timestamp`, `Engine_Temp_C`, `Oil_Pressure_psi`, `RPM`,
`Vibration_mm_s`, `Status`.

---

## 1. Import & Structure (FR-001, FR-007, FR-008, FR-010)
- File type: CSV
- Row count: **61**, Column count: **7**
- Column types: `Sample_ID` (numeric/int), `Timestamp` (datetime), `Engine_Temp_C` / `Oil_Pressure_psi`
  / `RPM` / `Vibration_mm_s` (numeric/float), `Status` (categorical)

## 2. Preprocessing (FR-012, FR-013, FR-014, FR-015)
| Check | Expected Result |
|---|---|
| Missing values | `Oil_Pressure_psi` has **2** missing values, at `Sample_ID` 10 and 11. All other columns: 0 missing. |
| Duplicate rows | **1** exact duplicate row — the row with `Sample_ID = 19` appears twice (rows at index 18 and 19 after import). Removing duplicates brings the row count to **60**. |
| Inconsistent categorical formatting | `Status` column contains `"Nominal"` (56 rows), plus formatting variants: `"nominal"` (1), `"NOMINAL"` (1), `"Nominal "` — trailing space (1), and two genuine distinct values `"Warning"` (1) and `"Critical"` (1). After normalization (case-fold + trim), there should be exactly 4 distinct status values: `Nominal` (59), `Warning` (1), `Critical` (1). |

After cleaning (duplicates dropped, `Oil_Pressure_psi` missing values filled with the column mean): **60 rows**.

## 3. Statistics — after cleaning (FR-021–FR-023)

| Column | Mean | Std Dev (ddof=1) | Min | Max | Q1 | Q3 | IQR |
|---|---|---|---|---|---|---|---|
| `Engine_Temp_C` | 91.751 | 5.931 | 86.850 | 134.500 | 89.735 | 92.752 | 3.017 |
| `Oil_Pressure_psi` | 39.651 | 1.619 | 36.120 | 43.140 | 38.537 | 40.873 | 2.335 |
| `RPM` | 2495.343 | 19.255 | 2456.800 | 2540.000 | 2484.700 | 2511.250 | 26.550 |
| `Vibration_mm_s` | 0.256 | 0.056 | 0.186 | 0.620 | 0.229 | 0.269 | 0.040 |

## 4. Trend Analysis (FR-024, FR-036)
- Sequence axis: `Sample_ID` (or `Timestamp`, equivalent ordering)
- `Engine_Temp_C` linear fit: **slope ≈ 0.1382 / sample**, intercept ≈ 87.53
- Total predicted change over 60 samples ≈ 8.29°C, compared to the "Stable" bar of `0.5 × std_dev`
  (≈ 2.97) → classifies as **"Increasing"** (see `implementation_specification.md` §4)
- This should trigger **RULE-002 (Sustained Upward Drift)** for `Engine_Temp_C`.

## 5. Correlation (FR-025, FR-026)
- `RPM` ↔ `Oil_Pressure_psi`: **r ≈ 0.934** — a strong correlation (above the default 0.7 threshold).
- This should trigger **RULE-005 (Strong Correlated Channels)** for this pair.
- All other column pairs: weak correlation (|r| well under 0.7); none should trigger RULE-005.

## 6. Anomaly Detection (FR-031–FR-035)

| Method | Column | Row (`Sample_ID`) | Value | Detail |
|---|---|---|---|---|
| Z-score (\|z\|>3) | `Engine_Temp_C` | **45** | 134.5 | z ≈ 7.21 |
| Z-score (\|z\|>3) | `Vibration_mm_s` | **30** | 0.62 | z ≈ 6.45 |
| IQR (1.5×) | `Engine_Temp_C` | **45** | 134.5 | bounds ≈ (85.21, 97.28) |
| IQR (1.5×) | `Vibration_mm_s` | **30** | 0.62 | bounds ≈ (0.17, 0.33) |
| Isolation Forest (contamination=0.05, n_estimators=100, random_state=42) | multivariate | **30, 45, 59** | — | Row 59 is flagged only by the multivariate method — none of its individual values are extreme on their own; this is the intended illustration of FR-033's value over single-column methods. |

## 7. Rule Engine Expected Firings (using `seed_files/engineering_rules.json`)

| Rule | Expected to Fire? | Why |
|---|---|---|
| RULE-001 (Critical Threshold Breach, `Engine_Temp_C > 120`) | **Yes** — at `Sample_ID` 45 (134.5 > 120) | Severity: Critical |
| RULE-002 (Sustained Upward Drift, `trend_slope > 0.05`) | **Yes** — for `Engine_Temp_C` (slope ≈ 0.138) | Severity: Warning |
| RULE-003 (High Variance Instability, `coefficient_of_variation > 0.15`) | **Yes** — for `Vibration_mm_s` only (CV ≈ 0.219; all other columns are well under 0.15, e.g. `Engine_Temp_C` CV ≈ 0.065) | Severity: Warning |
| RULE-004 (Repeated Threshold Breach, `anomaly_count(ThresholdBreach) >= 2`) | **No** — only one `ThresholdBreach` anomaly exists for `Engine_Temp_C` | This is an intentional non-firing case — a correct implementation should NOT flag this rule here. |
| RULE-005 (Strong Correlated Channels, `correlation > 0.7`) | **Yes** — for the `RPM` ↔ `Oil_Pressure_psi` pair (r ≈ 0.934) | Severity: Info |
| RULE-006 (Multivariate Anomaly Cluster, `isolation_forest_flag == true`) | **Yes** — at `Sample_ID` 30, 45, and 59 | Severity: Warning |

## 8. Overall Expected Session Outcome
- **Findings count:** non-zero (multiple anomalies + multiple rule matches — this is NOT a "No
  significant findings" case; FR-064's empty-case message should not appear for this dataset).
- **Highest severity present:** Critical (from RULE-001).
- **Recommendations should be ranked** with RULE-001's and RULE-004-style critical items first — since
  RULE-004 does not fire here, RULE-001's recommendation ("Immediately inspect the cooling system...")
  should be the top-ranked recommendation, per FR-061.

---

*Use this dataset as the first thing you run through a new AEIA build. If your numbers match the
table above, Modules 1–7 are wired correctly end-to-end.*
