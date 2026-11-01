# Anomaly scenarios

The challenge dataset contains five positive labels and one `AnomalyFixtureEvidence` row per label. Evidence is not a bypass: validator exclusions apply only to the exact labelled record, while unrelated violations remain failures.

| Issue | Repaired reference | Evidence |
|---|---|---|
| ANOM-00001 — unavailable interviewer | `INT-2026-000466`, interviewer `66` | Interview is scheduled while interviewer 66 is inactive |
| ANOM-00002 — duplicate application | `APP-REQ-2026-000015-CAND-001226` | Existing pair is referenced; no duplicate row is inserted |
| ANOM-00003 — missing feedback | `INT-2026-000015`, application `APP-REQ-2026-000087-CAND-000998` | Interview completed with no feedback row |
| ANOM-00004 — salary outside band | `OFF-2026-000001` | Pending offer salary is outside its requisition band |
| ANOM-00005 — closed requisition with active application | `REQ-2026-000051`, application `APP-REQ-2026-000051-CAND-000002` | Requisition closed while exactly that application remains active |

## Scenario details

### Unavailable interviewer

Normal scheduling rejects inactive interviewers. The fixture deactivates interviewer 66 but retains scheduled interview `INT-2026-000466`, making the validator and scheduling rule inspectable. The exclusion is limited to the evidence-linked interview.

### Duplicate application attempt

The database constraint `uq_application_pair` prevents a second row for the same requisition and candidate. The fixture therefore records a rejected duplicate attempt in evidence and keeps exactly one application row. This represents the business failure without corrupting the relational invariant.

### Missing interview feedback

`INT-2026-000015` is completed and its application is at `Interview Completed`, but no feedback row exists. The repair records the two lifecycle events needed to explain the application change. The validator excludes only this evidence-linked interview from the ordinary missing-feedback check.

### Salary outside approved band

`OFF-2026-000001` is reset to `Pending Approval`, approval metadata is cleared, and salary is set outside the linked requisition band. Normal approval rejects it. The validator excludes only this offer from the ordinary salary-band check and still checks reconciliation.

### Closed requisition with active application

`REQ-2026-000051` is closed while `APP-REQ-2026-000051-CAND-000002` remains active. Other active applications are transitioned to `Rejected` with valid events and audit rows, so exactly one labelled active application remains. The validator excludes this evidence-linked requisition from the ordinary closed-requisition check and separately verifies the labelled active application.

## Ground truth and exports

Anomalies are exported separately as `exports/ground_truth.csv` and `exports/ground_truth.json`; the complete anomaly table is also exported under the CSV/JSON table directories. The `anomaly_fixture_evidence` table supplies relational evidence for validators and tests.
