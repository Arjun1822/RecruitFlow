# Entity relationships

The diagram reflects the foreign keys in `backend/database/models.py`.

```mermaid
erDiagram
  departments ||--o{ job_requisitions : contains
  departments ||--o{ interviewers : assigns
  job_requisitions ||--o{ applications : receives
  job_requisitions ||--o{ screening_rules : configures
  candidates ||--o{ applications : submits
  candidates ||--o{ resume_artifacts : owns
  candidates ||--o{ candidate_skills : has
  skills ||--o{ candidate_skills : maps
  applications ||--o{ application_events : records
  applications ||--o{ interviews : schedules
  interviewers ||--o{ interviews : conducts
  interviews ||--o{ feedback : receives
  applications ||--o| offers : receives
  anomalies ||--o{ anomaly_fixture_evidence : explains
  anomalies ||--o{ exception_resolutions : resolves
```

`approval_history`, `audit_logs`, and `users` use entity identifiers or actors
without database foreign keys to every possible business entity. The detailed
column contract is in [data_dictionary.md](data_dictionary.md).
