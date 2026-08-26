# DealerDOH Human UAT — Findings Log (Sprint 16, Rail M)

Structured evidence log for real human sessions. Method:
[`UAT_PLAN.md`](UAT_PLAN.md). Script: [`UAT_SCRIPT.md`](UAT_SCRIPT.md).

**Integrity rules:**

- Every finding traces to an actual observed moment in a real
  session. **Nothing here may be fabricated, inferred from automated
  testing, or written before the session happened.**
- Participants appear only as `Manager-01` / `LotStaff-01` /
  `SalesManager-01` (…-02, …). No personal information.
- Record product behavior, never employee evaluation.
- One observed behavior per finding. Split compound observations.
- IDs: `UAT-M-###` (Manager sessions), `UAT-L-###` (Lot Staff),
  `UAT-S-###` (Sales Manager exploratory / Sales Operations
  Discovery). IDs are permanent once assigned — never renumber.

**Severity categories** (definitions in `UAT_PLAN.md` §7):
`Blocking` · `Severe friction` · `Moderate friction` ·
`Minor friction` · `Positive validation` · `Discovery` ·
`Not actionable`

**Dispositions:** `Open` → one of `Fixed (PR #…)` ·
`Fix planned (P0–P3)` · `Deferred — post-v1.1 (rationale)` ·
`Accepted as designed (rationale)` · `Roadmap (Sales Operations
Discovery)` · `Not actionable`. Human-caused findings are re-marked
resolved only after a human re-ran the scenario
(`UAT_PLAN.md` §9).

---

## Finding template

```markdown
### UAT-X-### — <short title>

- **Date/session:** YYYY-MM-DD / <Role-NN>
- **Scenario/workflow:** <M1–M7 / L1–L9 / S1–S7 / exploratory>
- **Observed behavior:** <what the participant actually did/said,
  with rough timing where meaningful>
- **Quote (optional):** "<short verbatim quote>"
- **Severity/category:** <one category>
- **Expected behavior:** <what the product intends>
- **Actual behavior:** <what the product did / communicated>
- **Coaching required:** <none / what was said, after how long>
- **Product implication:** <what this says about the product>
- **Recommended action:** <fix / defer / accept / roadmap — with
  priority P0–P3 if a fix>
- **Disposition:** Open
- **Linked issue/PR:** —
```

---

## Findings

*(none yet — human sessions have not occurred; this log is
intentionally empty until the owner conducts real sessions)*

---

## Sales Operations Discovery

*(S-session findings land here; roadmap input, not Sprint 16
implementation work)*

*(none yet)*

---

## Session index

| Session | Date | Role account | Scenarios covered | Start–end | Findings |
|---|---|---|---|---|---|
| *(none yet)* | | | | | |
