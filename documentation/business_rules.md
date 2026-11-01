# Business rules

* Requisitions must be approved before application intake; closed requisitions cannot receive new applications.
* Application status changes must follow the transition graph in `backend/services/application_service.py`.
* Progression beyond an interview requires completed feedback.
* Screening is explainable and uses required skills, preferred skills, experience, education/qualification proxy and projects; protected characteristics are not stored or used.
* Interview windows must have a positive duration and cannot overlap a scheduled or completed interview for the same interviewer.
* Offers require a selected application and approval inside the requisition salary band.
* Application events, approvals, and audit records preserve history rather than overwriting decisions.
