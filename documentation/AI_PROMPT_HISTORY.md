# AI Prompt History

## Purpose

This document is a transparent template for recording AI-assisted development
work. 
## Historical coverage

The repository does not contain a complete export of every ChatGPT, GitHub
Copilot.

## ChatGPT
October 2026

Help me plan and build an end-to-end Recruitment Management System for the YottaFlex.ai challenge.

Project planning and architecture

Received guidance on project structure, backend, frontend, database, and workflow.

October 2026

Help me implement recruitment workflows, including requisitions, candidates, applications, interviews, feedback, and offers.

Backend development

Received implementation guidance for APIs, database models, and business rules.

October 2026

Help me improve the RecruitFlow user interface and connect the frontend with the backend APIs.

Frontend development

Received guidance on React pages, API integration, and user workflows.

October 2026

Help me generate deterministic synthetic recruitment data with the required baseline counts and five anomaly scenarios.

Data generation

Received guidance on seeded data, validation, anomaly fixtures, and exports.

October–November 2026

Review the project test results, identify gaps, and help improve the documentation.

Testing and documentation

Received assistance reviewing validation evidence, limitations, and technical documentation.

November 2026

Help me prepare the AI prompt history and AI usage disclosure for the challenge submission.

Submission preparation

Prepared transparent AI usage records and disclosure content.
## GitHub Copilot

# ROLE: Senior Full-Stack Developer, Database Architect & Data Engineer

Act as a senior software engineer, database architect, Python developer, and data engineer. Build a complete, functional, end-to-end **Recruitment Management System (RMS)**.

Do not just generate sample code or a UI prototype. Build a working application with a properly normalized database, realistic synthetic data, business logic, validation, exception handling, analytics dashboards, and complete documentation.

Work directly in the current project workspace. Create all required files, install necessary dependencies, execute the application, run tests, debug errors, and verify that the complete workflow works.

# 1. PROJECT OBJECTIVE

Develop a Recruitment Management System that manages the complete employee hiring lifecycle:

1. Job requisition creation and approval.
2. Candidate registration and management.
3. Resume upload and metadata management.
4. Candidate job applications.
5. Job-related resume screening and scoring.
6. Interview scheduling and interviewer availability.
7. Structured interview feedback.
8. Candidate stage progression.
9. Offer creation and approval.
10. Recruitment analytics and reporting.

The application must expose important business decisions, exceptions, audit history, and measurable recruitment metrics.

# 2. TECHNOLOGY STACK

Use the following technologies:

- Backend: Python 3.x
- Frontend: Streamlit
- Database: MySQL 8.x
- Database connectivity: SQLAlchemy and PyMySQL
- Data processing: Pandas and NumPy
- Synthetic data generation: Python Faker and seeded random generation
- Visualization: Plotly
- Validation: Pydantic and custom validation functions
- Testing: Pytest
- Configuration: Python dotenv
- Export: CSV, JSON and SQL

Use a modular architecture with separate files for database connections, models, services, business logic, data generation, validation and UI.

# 3. DATABASE DESIGN

Create the following 12 core entities:

1. Department
2. JobRequisition
3. Candidate
4. Application
5. ResumeArtifact
6. Skill
7. CandidateSkill
8. ScreeningRule
9. Interview
10. Interviewer
11. Feedback
12. Offer

Requirements:

- Define a primary key for every table.
- Define foreign keys for every relationship.
- Add appropriate indexes and unique constraints.
- Use bridge tables for many-to-many relationships.
- Define appropriate data types and nullability.
- Add created_at and updated_at timestamps where appropriate.
- Store lifecycle status and state-change history.
- Avoid duplicate and redundant data.
- Use database transactions for critical operations.
- Document 1:1, 1:N and N:M relationships.
- Include effective dates where applicable.

Create an additional ApplicationEvent or StatusHistory table to preserve candidate application stage changes.

Create an ApprovalHistory table to track requisition and offer approvals.

Create an AuditLog table to record important system actions.

# 4. ID GENERATION CONVENTIONS

Follow these exact naming conventions:

- Requisition: REQ-2026-000001
- Candidate: CAND-000001
- Application: APP-<requisition-id>-<candidate-id>
- Interview: INT-2026-000001
- Feedback: FB-<interview-id>-<interviewer-id>
- Offer: OFF-2026-000001

Requirements:

- IDs must be deterministic.
- IDs must be immutable.
- Counters must be zero-padded.
- All foreign-key references must match exactly.
- Prevent duplicate IDs.

# 5. DATA DICTIONARY

Create a complete data dictionary for all 12 core entities.

For every column, document:

- Column name.
- Data type.
- Description.
- Required or optional.
- Allowed values.
- Default value.
- Unique constraint.
- Validation rules.
- Primary key or foreign key designation.
- Units where applicable.

Export the data dictionary as Markdown and Excel.

# 6. SYNTHETIC DATA GENERATION

Generate the following baseline dataset:

- 100 Job Requisitions.
- 2,000 Candidates.
- 3,000 Applications.
- 600 Interviews.
- 150 Offers.

Generate the necessary additional records for departments, skills, candidate skills, screening rules, interviewers, feedback, approval history, status history, and audit logs.

Use only fictional, non-sensitive candidate information.

Use a fixed random seed:

20261022

Requirements:

- Parameterize dataset size.
- Support both starter and full datasets.
- Generate parent/master records before dependent records.
- Maintain valid primary and foreign keys.
- Generate realistic distributions.
- Include different job roles and departments.
- Include freshers and experienced candidates.
- Include varied candidate skills and missing skills.
- Include applications with different lifecycle statuses.
- Include accepted, rejected, pending and withdrawn applications.
- Include accepted, rejected and pending offers.
- Generate derived scores, statuses, totals and dates from source records.
- Do not generate logically independent random values for derived fields.

The same seed and configuration must produce the same dataset.

# 7. BUSINESS LOGIC

Implement the following rules.

A. Job Requisition Management

- Business requester creates a requisition.
- Approver reviews and approves or rejects it.
- Only approved requisitions can receive new applications.
- Every requisition must contain required skills.
- Requisition includes department, job title, openings, experience range, salary range, location and status.
- Closed requisitions cannot receive new applications.

B. Candidate Management

- Create synthetic candidate profiles.
- Store resume metadata.
- Allow multiple skills per candidate.
- Prevent duplicate candidate identities using defined matching rules.
- Support multiple resume versions.

C. Application Management

- Link candidates to requisitions.
- Generate unique application IDs.
- Detect duplicate applications for the same candidate and requisition.
- Track application status and status history.
- Support withdrawal and rejection.

D. Resume Screening

Create a configurable screening engine.

Example scoring criteria:

- Required technical skills: 40 points.
- Relevant experience: 20 points.
- Preferred skills: 20 points.
- Education/job-specific qualifications: 10 points.
- Relevant project experience: 10 points.

Total score: 100.

Important:
- Score only job-related criteria.
- Do not use gender, religion, caste, ethnicity, age, disability or other protected characteristics.
- Do not use demographic proxies.
- Show matched skills.
- Show missing skills.
- Explain the score.
- Store screening results and rule versions.
- Make screening decisions explainable.
- Do not automatically reject candidates based solely on an opaque score.

E. Interview Scheduling

- Support multiple interview rounds.
- Assign interviewers.
- Track interviewer availability.
- Validate interview date and time.
- Detect overlapping interviews.
- Prevent scheduling with unavailable interviewers.
- Track scheduled, completed, cancelled and rescheduled interviews.
- Store interview history.

F. Structured Feedback

Capture:
- Technical knowledge rating.
- Problem-solving rating.
- Communication rating.
- Role-specific skills rating.
- Overall rating.
- Strengths.
- Weaknesses.
- Interviewer comments.
- Recommendation: Strong Hire, Hire, Hold or Reject.

Feedback must be submitted before the application can progress to the next required stage.

G. Candidate Stage Progression

Support these stages:

Applied → Screening → Shortlisted → Interview Scheduled → Interview Completed → Selected → Offer Pending → Offer Released → Hired.

Also support:
- Rejected.
- Withdrawn.
- On Hold.

Enforce valid state transitions.

Store every stage transition in application history.

H. Offer Management

- Create offers only after required interview stages are completed.
- Require authorized approval.
- Validate salary against approved requisition salary bands.
- Prevent unapproved offers from being released.
- Track offer status.
- Support accepted, rejected, expired and withdrawn offers.
- Store approval and offer history.

# 8. REQUIRED NEGATIVE SCENARIOS

Generate valid baseline data first.

Then inject separately labelled edge cases:

1. Interview scheduled for an unavailable interviewer.
2. Candidate applied twice for the same requisition.
3. Missing interview feedback but application stage advanced.
4. Offer salary outside approved salary band.
5. Closed requisition with active applications.

For every edge case:

- Assign a unique issue ID.
- Store issue_type.
- Store affected entity ID.
- Store expected outcome.
- Store ground_truth label.
- Store severity.
- Store a description.

Do not corrupt unrelated records.

Create separate files:

- ground_truth.csv
- ground_truth.json

Never use ground-truth labels as input features for detection or screening.

# 9. VALIDATION ENGINE

Implement automated checks for:

- Primary-key uniqueness.
- Foreign-key integrity.
- Duplicate applications.
- Invalid enumeration values.
- Missing mandatory fields.
- Invalid dates.
- Interview scheduling conflicts.
- Missing feedback.
- Invalid lifecycle transitions.
- Salary band violations.
- Offer approval violations.
- Closed requisitions with active applications.
- Application and offer status reconciliation.
- Derived-value consistency.
- Record counts.

Generate:

validation_summary.csv
validation_report.json

Show passed checks, failed checks, severity and affected record IDs.

# 10. STREAMLIT USER INTERFACE

Create a professional, modern, responsive recruitment dashboard.

Use a clean design with consistent colors, typography, sidebar navigation and interactive charts.

Create these pages:

1. Dashboard
   - Total requisitions.
   - Total candidates.
   - Total applications.
   - Shortlisted candidates.
   - Interviews scheduled.
   - Offers released.
   - Offers accepted.
   - Hiring conversion rate.

2. Requisition Management
   - Create requisitions.
   - Edit requisitions.
   - Approve/reject requisitions.
   - View required skills.
   - Track requisition status.

3. Candidate Management
   - Add candidates.
   - Search candidates.
   - View candidate profiles.
   - Upload resumes.
   - Manage skills.

4. Application Management
   - Apply candidates to jobs.
   - View applications.
   - Track application stages.
   - Detect duplicates.
   - View application history.

5. Resume Screening
   - Run screening.
   - Display candidate scores.
   - Show matched and missing skills.
   - Explain scoring decisions.
   - Compare candidates.

6. Interview Management
   - Schedule interviews.
   - Assign interviewers.
   - Check availability.
   - Display scheduling conflicts.
   - Reschedule or cancel interviews.

7. Feedback Management
   - Submit structured feedback.
   - View interviewer evaluations.
   - Display recommendations.
   - Block progression when required feedback is missing.

8. Offer Management
   - Create offers.
   - Validate salary bands.
   - Submit approvals.
   - Approve or reject offers.
   - Track acceptance and rejection.

9. Exception Management
   - Display all five required anomalies.
   - Show severity and affected records.
   - Display expected and actual outcomes.
   - Allow authorized users to resolve issues.
   - Maintain resolution history.

10. Reports and Analytics
    - Recruitment funnel.
    - Applications by department.
    - Candidates by job role.
    - Screening score distribution.
    - Interview pass rate.
    - Offer acceptance rate.
    - Time to hire.
    - Requisition fulfilment rate.
    - Interviewer workload.
    - Exception detection accuracy.

11. Administration
    - Manage departments.
    - Manage skills.
    - Manage interviewers.
    - Configure screening rules.
    - Manage users and roles.

# 11. USER ROLES AND PERMISSIONS

Implement role-based access control.

Roles:

- Business Requester.
- Process Owner.
- Approver.
- Operations Analyst.
- System Administrator.

Enforce permissions in the backend, not only by hiding UI controls.

Record important actions in AuditLog.

Use secure password hashing and environment-based configuration.

Do not hardcode database passwords or API keys.

# 12. ANALYTICS AND KPIs

Calculate all metrics from database records.

Include:

- Total applications.
- Screening pass rate.
- Interview completion rate.
- Interview pass rate.
- Offer release rate.
- Offer acceptance rate.
- Time to hire.
- Requisition fulfilment rate.
- Candidate withdrawal rate.
- Interviewer utilization.
- Exception detection precision.
- Exception detection recall.

Clearly define each KPI formula.

Do not invent metrics or display hardcoded dashboard numbers.

# 13. EXPORT AND REPORTING

Support exporting:

- Every entity as CSV.
- Every entity as JSON.
- SQL schema and seed data.
- Ground truth.
- Validation reports.
- Data dictionary.
- Recruitment analytics reports.

Create a source manifest documenting:

- Dataset filename.
- Record count.
- Generation method.
- Random seed.
- Generation timestamp.
- Dataset version.
- Data provenance.
- License details for any external data used.

Prefer fully synthetic data and do not use unauthorized personal data.

# 14. PROJECT FOLDER STRUCTURE

Create a modular structure similar to:

recruitment_management_system/
│
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
│
├── database/
│   ├── connection.py
│   ├── schema.sql
│   ├── models.py
│   └── seed.py
│
├── data_generator/
│   ├── generator.py
│   ├── master_data.py
│   ├── transaction_data.py
│   ├── anomaly_generator.py
│   └── export_data.py
│
├── services/
│   ├── requisition_service.py
│   ├── candidate_service.py
│   ├── application_service.py
│   ├── screening_service.py
│   ├── interview_service.py
│   ├── feedback_service.py
│   └── offer_service.py
│
├── validation/
│   ├── validator.py
│   ├── integrity_checks.py
│   ├── business_rule_checks.py
│   └── validation_report.py
│
├── analytics/
│   ├── metrics.py
│   └── reports.py
│
├── ui/
│   ├── dashboard.py
│   ├── requisitions.py
│   ├── candidates.py
│   ├── applications.py
│   ├── screening.py
│   ├── interviews.py
│   ├── feedback.py
│   ├── offers.py
│   ├── exceptions.py
│   └── reports.py
│
├── tests/
│   ├── test_database.py
│   ├── test_generator.py
│   ├── test_screening.py
│   ├── test_interviews.py
│   ├── test_offers.py
│   └── test_validation.py
│
├── exports/
│   ├── csv/
│   ├── json/
│   └── sql/
│
└── documentation/
    ├── ER_diagram.md
    ├── data_dictionary.md
    ├── business_rules.md
    ├── validation_summary.md
    └── source_manifest.md

# 15. TESTING REQUIREMENTS

Write automated tests for:

- Database connectivity.
- Table creation.
- Primary-key uniqueness.
- Foreign-key integrity.
- Deterministic ID generation.
- Reproducible data generation.
- Screening calculations.
- Duplicate application detection.
- Interview availability.
- Interview conflicts.
- Missing feedback restrictions.
- Candidate lifecycle transitions.
- Offer approval.
- Salary validation.
- Exception detection.
- KPI calculations.

Run all tests and fix failures.

Generate the dataset twice using the same seed and configuration.

Compare:
- Record counts.
- File checksums.
- Generated IDs.
- Derived values.

Demonstrate reproducibility.

# 16. README AND DOCUMENTATION

Create a complete README containing:

- Project introduction.
- Business problem.
- Project objectives.
- Features.
- Technology stack.
- System architecture.
- ER diagram.
- Database setup instructions.
- Environment configuration.
- Installation instructions.
- Data generation commands.
- Validation commands.
- Application execution commands.
- Test execution commands.
- Export instructions.
- Sample login credentials for development.
- Known limitations.

# 17. EXECUTION COMMANDS

Provide working commands similar to:

Install dependencies:
pip install -r requirements.txt

Generate starter data:
python -m data_generator.generator --size starter --seed 20261022

Generate full data:
python -m data_generator.generator --size full --seed 20261022

Run validation:
python -m validation.validator

Run tests:
pytest -v

Launch application:
streamlit run app.py

Make sure these commands actually work.

# 18. DEVELOPMENT INSTRUCTIONS FOR THE AGENT

Follow this development sequence:

Phase 1: Inspect the workspace and establish the project structure.

Phase 2: Design the database schema, data dictionary and ER diagram.

Phase 3: Implement database connectivity and table creation.

Phase 4: Implement deterministic synthetic data generation.

Phase 5: Implement all recruitment business rules.

Phase 6: Implement exception generation and ground truth.

Phase 7: Implement validation and automated testing.

Phase 8: Implement all Streamlit dashboard pages.

Phase 9: Implement analytics and exports.

Phase 10: Write documentation and run end-to-end tests.

IMPORTANT EXECUTION RULES:

- Do not stop after generating the folder structure.
- Do not provide only theoretical explanations.
- Create actual working source files.
- Do not leave placeholder functions or TODO comments for core features.
- Do not use hardcoded analytics values.
- Do not silently ignore errors.
- Do not generate invalid foreign keys.
- Do not mix ground truth with input data.
- Do not bypass business rules.
- Do not claim a test passed without running it.
- Do not claim the application works unless you execute and verify it.
- If a dependency or database service is unavailable, explain the limitation and implement the available parts without pretending they were verified.
- Make reasonable technical decisions independently.
- After each phase, run appropriate checks before proceeding.
- Preserve existing user files and code unless modification is necessary.

# FINAL ACCEPTANCE CRITERIA

The project is complete only when:

1. All required database tables exist.
2. All relationships and constraints work.
3. The specified synthetic dataset is generated.
4. All IDs and foreign keys are consistent.
5. All recruitment workflow rules are enforced.
6. All five negative scenarios are detected.
7. Ground truth is stored separately.
8. Validation reports are generated.
9. The Streamlit application runs.
10. All dashboard pages work.
11. KPIs are calculated from actual database records.
12. CSV, JSON and SQL exports work.
13. Automated tests pass.
14. Fixed-seed reproducibility is demonstrated.
15. README and technical documentation are complete.

Start building the complete project now. Work directly in the current workspace, execute the implementation, test it, and report the actual completed features, commands, test results and any remaining limitations.
->for QA
Act as a senior QA engineer. Audit the entire Recruitment Management System you just built.

Do not just review the code visually. Execute the application, connect to the database, generate the full dataset using seed 20261022, run every validation check, execute all automated tests, and test the complete recruitment workflow.

Specifically verify:
1. All 12 core entities and additional history/audit tables.
2. All primary keys and foreign keys.
3. Exactly 100 requisitions, 2,000 candidates, 3,000 applications, 600 interviews and 150 offers.
4. All five required anomaly scenarios.
5. Separate ground_truth files.
6. Screening calculations and candidate stage transitions.
7. Interview availability and feedback restrictions.
8. Offer approvals and salary-band validation.
9. Dashboard metrics against actual SQL query results.
10. CSV, JSON and SQL exports.
11. Fixed-seed reproducibility.

Fix every issue you discover. Rerun the affected tests and provide an honest final QA report with passed tests, failed tests, corrected issues and remaining limitations. Never mark unexecuted tests as passed.


## Other AI tools
NOT USED

