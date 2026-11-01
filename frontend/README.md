# Recruitment Management System frontend

The Streamlit entry point is [app.py](app.py). It renders the dashboard, recruitment management screens, workflow actions, analytics, validation, exception management, and administration views.

Run it from the repository root:

```powershell
streamlit run frontend/app.py
```

The frontend imports business operations from `backend.services`, `backend.authentication`, `backend.analytics`, and `backend.validation`; database and workflow rules remain in the backend.
