-- SQLAlchemy-generated schema and seed export
BEGIN;

CREATE TABLE anomalies (
	issue_id VARCHAR(25) NOT NULL, 
	issue_type VARCHAR(80) NOT NULL, 
	entity_id VARCHAR(60) NOT NULL, 
	expected_outcome TEXT NOT NULL, 
	ground_truth VARCHAR(20) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	description TEXT NOT NULL, 
	resolved BOOL NOT NULL, 
	PRIMARY KEY (issue_id)
)

;

CREATE TABLE approval_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	entity_type VARCHAR(30) NOT NULL, 
	entity_id VARCHAR(60) NOT NULL, 
	decision VARCHAR(20) NOT NULL, 
	approver VARCHAR(100) NOT NULL, 
	reason TEXT, 
	decided_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE audit_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	actor VARCHAR(100) NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id VARCHAR(60) NOT NULL, 
	details TEXT, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE candidates (
	id VARCHAR(20) NOT NULL, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	education VARCHAR(150) NOT NULL, 
	years_experience INTEGER NOT NULL, 
	location VARCHAR(100) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;

CREATE TABLE departments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;

CREATE TABLE skills (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(80) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(40) NOT NULL, 
	active BOOL NOT NULL, 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until DATETIME, 
	last_login_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE candidate_skills (
	candidate_id VARCHAR(20) NOT NULL, 
	skill_id INTEGER NOT NULL, 
	proficiency VARCHAR(20) NOT NULL, 
	PRIMARY KEY (candidate_id, skill_id), 
	FOREIGN KEY(candidate_id) REFERENCES candidates (id), 
	FOREIGN KEY(skill_id) REFERENCES skills (id)
)

;

CREATE TABLE exception_resolutions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	issue_id VARCHAR(25) NOT NULL, 
	actor VARCHAR(100) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	notes TEXT NOT NULL, 
	resolved_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES anomalies (issue_id)
)

;

CREATE TABLE interviewers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	department_id INTEGER, 
	active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
)

;

CREATE TABLE job_requisitions (
	id VARCHAR(24) NOT NULL, 
	department_id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	openings INTEGER NOT NULL, 
	min_experience INTEGER NOT NULL, 
	max_experience INTEGER NOT NULL, 
	min_salary FLOAT NOT NULL, 
	max_salary FLOAT NOT NULL, 
	location VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	requested_by VARCHAR(100) NOT NULL, 
	approved_by VARCHAR(100), 
	effective_from DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
)

;

CREATE TABLE resume_artifacts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	candidate_id VARCHAR(20) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_path VARCHAR(500) NOT NULL, 
	version INTEGER NOT NULL, 
	uploaded_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(candidate_id) REFERENCES candidates (id)
)

;

CREATE TABLE applications (
	id VARCHAR(60) NOT NULL, 
	requisition_id VARCHAR(24) NOT NULL, 
	candidate_id VARCHAR(20) NOT NULL, 
	status VARCHAR(35) NOT NULL, 
	applied_at DATETIME NOT NULL, 
	screening_score FLOAT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_application_pair UNIQUE (requisition_id, candidate_id), 
	FOREIGN KEY(requisition_id) REFERENCES job_requisitions (id), 
	FOREIGN KEY(candidate_id) REFERENCES candidates (id)
)

;

CREATE TABLE screening_rules (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	requisition_id VARCHAR(24) NOT NULL, 
	required_skills TEXT NOT NULL, 
	preferred_skills TEXT NOT NULL, 
	version INTEGER NOT NULL, 
	active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requisition_id) REFERENCES job_requisitions (id)
)

;

CREATE TABLE application_events (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	application_id VARCHAR(60) NOT NULL, 
	from_status VARCHAR(35), 
	to_status VARCHAR(35) NOT NULL, 
	changed_by VARCHAR(100) NOT NULL, 
	changed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id)
)

;

CREATE TABLE interviews (
	id VARCHAR(24) NOT NULL, 
	application_id VARCHAR(60) NOT NULL, 
	interviewer_id INTEGER NOT NULL, 
	round_number INTEGER NOT NULL, 
	starts_at DATETIME NOT NULL, 
	ends_at DATETIME NOT NULL, 
	status VARCHAR(25) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id), 
	FOREIGN KEY(interviewer_id) REFERENCES interviewers (id)
)

;

CREATE TABLE offers (
	id VARCHAR(24) NOT NULL, 
	application_id VARCHAR(60) NOT NULL, 
	salary FLOAT NOT NULL, 
	status VARCHAR(25) NOT NULL, 
	approved_by VARCHAR(100), 
	released_at DATETIME, 
	expires_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (application_id), 
	FOREIGN KEY(application_id) REFERENCES applications (id)
)

;

CREATE TABLE feedback (
	id VARCHAR(40) NOT NULL, 
	interview_id VARCHAR(24) NOT NULL, 
	interviewer_id INTEGER NOT NULL, 
	technical_rating INTEGER NOT NULL, 
	problem_solving_rating INTEGER NOT NULL, 
	communication_rating INTEGER NOT NULL, 
	role_skills_rating INTEGER NOT NULL, 
	overall_rating FLOAT NOT NULL, 
	strengths TEXT NOT NULL, 
	weaknesses TEXT NOT NULL, 
	comments TEXT NOT NULL, 
	recommendation VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id), 
	FOREIGN KEY(interviewer_id) REFERENCES interviewers (id)
)

;
COMMIT;