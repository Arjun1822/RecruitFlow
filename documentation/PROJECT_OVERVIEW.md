# RecruitFlow — project overview

## Introduction

RecruitFlow is a recruitment lifecycle management system for managing requisitions, candidates, applications, screening, interviews, feedback, offers, approvals, audit history, exceptions, and analytics. The implementation combines a FastAPI service, SQLAlchemy persistence, a React/Vite workspace, and a retained Streamlit console.

## Problem and objectives

Recruiting work is often spread across spreadsheets and disconnected tools. RecruitFlow provides one auditable workflow from an approved requisition to a hiring outcome. The implementation objectives are:

- enforce recruitment business rules at service boundaries;
- keep application stage changes explainable through lifecycle events;
- protect sensitive operations with authentication and role permissions;
- expose database-derived metrics and validation results;
- provide deterministic synthetic data for demonstrations and challenge evaluation; and
- preserve anomaly ground truth separately from ordinary data-quality failures.

## Implemented solution

The React workspace calls the FastAPI API over HTTP. The API delegates workflow decisions to services, uses SQLAlchemy sessions for MySQL 8, and records audit/history rows alongside material changes. The generator creates fictional, deterministic data with seed `20261022`; exports are written as CSV, JSON, SQL, and a data dictionary.

## Key features

- requisition creation, editing, approval, rejection, and closure;
- candidate and private PDF resume management;
- application uniqueness and explicit stage transition graph;
- explainable screening scores based on configured skills and experience;
- interviewer availability, overlap detection, scheduling, completion, cancellation, and rescheduling;
- structured feedback with rating bounds;
- offer creation, salary-band approval, release, and acceptance;
- role-based authorization and bcrypt password hashing;
- audit logs, approval history, application events, anomalies, and exception resolution;
- dashboard metrics, funnel reporting, department views, and validation; and
- reproducible starter/full synthetic datasets.

## Intended users

| Role | Implemented responsibility |
|---|---|
| Business Requester | Requisitions, candidates, and applications |
| Process Owner | Operational workflow, interviews, feedback, and offers |
| Approver | Requisition and offer decisions plus audit viewing |
| Operations Analyst | Candidates, applications, interviews, feedback, analytics, and exceptions |
| System Administrator | All permissions and user administration |

## Scope and status

The core workflow, API, React workspace, Streamlit console, generator, validator, exports, anomaly evidence, and test suites are implemented. MySQL is mandatory; SQLite is not a supported runtime fallback. MFA, SSO, password reset, and production secret-manager integration remain outside the implementation.

The recorded validation package reports the full baseline volumes as 100 requisitions, 2,000 candidates, 3,000 applications, 600 interviews, and 150 offers. See [TESTING_AND_VALIDATION.md](TESTING_AND_VALIDATION.md) for the distinction between recorded passes and currently blocked environment-dependent tests.

## Business value

RecruitFlow makes recruitment state visible, prevents invalid actions before persistence, leaves an audit trail for operational decisions, and gives reviewers a repeatable dataset for demonstrations and regression checks.
