-- MySQL 8 bootstrap. The authoritative schema is generated from database.models.
-- Run: python -m database.migrate
-- This file is intentionally idempotent for the new security and exception tables.
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(40) NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  locked_until DATETIME NULL,
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX ix_users_username (username),
  INDEX ix_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS exception_resolutions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id VARCHAR(25) NOT NULL,
  actor VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL,
  notes TEXT NOT NULL,
  resolved_at DATETIME NOT NULL,
  CONSTRAINT fk_resolution_anomaly FOREIGN KEY (issue_id) REFERENCES anomalies(issue_id),
  INDEX ix_exception_resolutions_issue_id (issue_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
