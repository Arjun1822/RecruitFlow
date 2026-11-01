# API documentation

Base URL: `http://localhost:8000`. Except `/health`, login, and logout, routes require `Authorization: Bearer <token>`. JSON rows contain the model columns; user responses remove `password_hash`.

## Authentication and dashboard

| Method and path | Request | Result |
|---|---|---|
| GET `/health` | none | `{"status":"ok"}` |
| POST `/api/auth/login` | `{username,password}` | Token and safe user; 401 invalid/locked |
| GET `/api/auth/register-admin/status` | none | Localhost only; reports whether one-time registration is available |
| POST `/api/auth/register-admin` | `{username,password,password_confirmation}` | Localhost-only first-admin registration; 201 success, 400 validation, 403 remote, 404 disabled/unavailable, 409 already registered |
| POST `/api/auth/logout` | none | `{"status":"ok"}`; token invalidation is client-side |
| GET `/api/auth/me` | none | Current safe user; 401 invalid token |
| GET `/api/dashboard/metrics` | none | Database-derived metric object |
| GET `/api/dashboard/application-stats` | none | Status-to-count map |
| GET `/api/dashboard/recruitment-funnel` | none | `{"stages": ...metrics}` |

## Requisitions, departments, and candidates

| Method and path | Request/query | Result and rules |
|---|---|---|
| GET `/api/requisitions` | `skip`, `limit<=100` | Paginated requisition rows |
| POST `/api/requisitions` | `department_id,title,openings,min_salary,max_salary,location` | Draft requisition; requires `manage_requisitions`; invalid band is 400 |
| GET `/api/requisitions/{requisition_id}` | path ID | One row or 404 |
| PUT `/api/requisitions/{requisition_id}` | same creation body | Updated row; requires permission |
| DELETE `/api/requisitions/{requisition_id}` | path ID | `{"status":"deleted"}`; requires permission |
| PUT `/api/requisitions/{requisition_id}/status` | `{"status":...}` | Status change; approval/rejection requires approver permission |
| GET `/api/departments` | none | Department rows |
| POST `/api/departments` | `name,description?` | New department; requires `manage_requisitions` |
| GET `/api/candidates` | `skip`, `limit<=100` | Paginated candidate rows |
| POST `/api/candidates` | `first_name,last_name,email,phone,education,years_experience,location` | Candidate row; requires `manage_candidates` |
| GET `/api/candidates/{candidate_id}` | path ID | One row or 404 |
| PUT `/api/candidates/{candidate_id}` | candidate body | Updated row; requires permission |

## Resumes and applications

| Method and path | Request | Result and rules |
|---|---|---|
| GET `/api/candidates/{candidate_id}/resumes` | path ID | Resume metadata or 404 candidate |
| POST `/api/candidates/{candidate_id}/resumes` | `filename,storage_path,version` | Metadata row; requires candidate permission |
| POST `/api/candidates/{candidate_id}/resumes/upload` | multipart PDF `file` | Private randomized storage; PDF signature and size/type checks |
| GET `/api/candidates/{candidate_id}/resumes/{resume_id}/download` | path IDs | PDF download for users with `manage_candidates`; path is confined to private root |
| GET `/api/applications` | `skip`, `limit<=100` | Paginated application rows |
| GET `/api/applications/{application_id}/history` | path ID | Ordered `ApplicationEvent` rows |
| POST `/api/applications` | `requisition_id,candidate_id` | Application plus initial event/audit; only approved requisitions, duplicate rejected |
| PUT `/api/applications/{application_id}/stage` | `{"status":...}` | Valid lifecycle transition or 400/403 |
| POST `/api/screening/evaluate` | `{"application_id":...}` | Score, matched/missing skills, rule version |
| GET `/api/screening/results` | none | Applications with screening scores |

## Interviews and feedback

| Method and path | Request | Result and rules |
|---|---|---|
| GET `/api/interviews` | none | Interview rows |
| GET `/api/interviewers` | none | Active interviewers |
| GET `/api/interviewers/{interviewer_id}/availability` | `starts_at`, `ends_at` | Availability and overlapping bookings; inactive/invalid range is 404/400 |
| POST `/api/interviews` | `application_id,interviewer_id,starts_at,ends_at,round_number?` | Scheduled interview; active interviewer and no overlap required |
| PUT `/api/interviews/{interview_id}` | status or schedule fields | Status update or reschedule; invalid state/range is 400 |
| GET `/api/feedback/{interview_id}` | path ID | Feedback or 404 |
| POST `/api/feedback` | interview, interviewer, four ratings, text, recommendation | Feedback after completion; assigned interviewer and no duplicate required |

## Offers, exceptions, validation, and analytics

| Method and path | Request/query | Result and rules |
|---|---|---|
| GET `/api/offers` | none | Offer rows |
| POST `/api/offers` | `application_id,salary` | Offer for selected/offer-pending application |
| PUT `/api/offers/{offer_id}/status` | `{"status":...}` | Accepted/Rejected/Expired/Withdrawn; acceptance requires released offer |
| PUT `/api/offers/{offer_id}/approve` | path ID | Salary-band approval; requires approver |
| PUT `/api/offers/{offer_id}/release` | path ID | Release approved offer |
| GET `/api/exceptions` | none | Anomaly rows |
| GET `/api/validation` | none | Validator checks |
| GET `/api/analytics/overview` | optional `start_date,end_date,department_id` | Metrics, stages, monthly trends, department statistics |
| GET `/api/analytics/hiring-funnel` | none | Funnel metrics |
| GET `/api/analytics/department-performance` | none | Department rows under `departments` |
| GET `/api/admin/users` | none | Safe user rows; requires `view_audit` |
| POST `/api/admin/users` | `username,password,role` | User row; requires administrator permission |

## Common errors

Pydantic validation returns 422. Missing or invalid authentication returns 401. Permission failures return 403. Service `ValueError` responses return 400. Missing resources generally return 404, duplicate feedback returns 409, and oversized uploads return 413.
