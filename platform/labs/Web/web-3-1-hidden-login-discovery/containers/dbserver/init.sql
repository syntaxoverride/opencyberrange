-- NovaTech Solutions. Production Database
-- Schema and seed data for the Hidden Login Discovery lab

CREATE DATABASE IF NOT EXISTS novatech;
USE novatech;

-- ── Application tables (realistic production schema) ─────────────────

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'manager', 'developer', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

INSERT INTO users (username, email, password_hash, role, last_login) VALUES
    ('admin', 'admin@novatech-solutions.com', '$2b$12$LJ3.Gz7y5rQ1X2kN8vF5m.fake_hash_do_not_use', 'admin', '2024-09-14 22:31:00'),
    ('dharris', 'devon.harris@novatech-solutions.com', '$2b$12$Km5.Rz8y3tP4W6kQ9vH7n.fake_hash_do_not_use', 'admin', '2024-09-15 08:14:00'),
    ('evasquez', 'elena.vasquez@novatech-solutions.com', '$2b$12$Np7.Tx2y1rS6U8kM3vJ9o.fake_hash_do_not_use', 'admin', '2024-09-10 16:45:00'),
    ('jchen', 'james.chen@novatech-solutions.com', '$2b$12$Qq9.Vy4y7tR8X0kP5vL1p.fake_hash_do_not_use', 'admin', '2024-09-13 11:22:00'),
    ('skim', 'sarah.kim@novatech-solutions.com', '$2b$12$Rs1.Wz6y9tT0Z2kR7vN3q.fake_hash_do_not_use', 'manager', '2024-09-15 09:01:00');

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    client VARCHAR(200) NOT NULL,
    status ENUM('active', 'completed', 'on-hold') DEFAULT 'active',
    budget DECIMAL(12, 2),
    start_date DATE,
    end_date DATE
);

INSERT INTO projects (name, client, status, budget, start_date, end_date) VALUES
    ('MedCore Patient Portal v3', 'MedCore Health Systems', 'active', 450000.00, '2024-06-01', '2025-02-28'),
    ('Apex Trading Platform', 'Apex Financial Group', 'active', 820000.00, '2024-03-15', '2025-01-31'),
    ('TransGlobal Route Optimizer', 'TransGlobal Logistics', 'completed', 310000.00, '2023-09-01', '2024-07-31'),
    ('NovaTech Website Redesign', 'Internal', 'active', 45000.00, '2024-08-01', '2024-10-31'),
    ('CloudBridge Migration Tool', 'Pinnacle Partners', 'on-hold', 175000.00, '2024-07-15', NULL);

-- ── Audit tokens table (contains assessment token 3) ─────────────────

CREATE TABLE audit_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_name VARCHAR(100) NOT NULL,
    token_value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

INSERT INTO audit_tokens (token_name, token_value, notes) VALUES
    ('db_health_check', 'healthy_2024Q3', 'Automated health check token'),
    ('backup_verification', 'bkp_verified_0914', 'Last backup verification marker'),
    ('assessment_marker', '3xp0s3d', 'Blackridge Security assessment token. do not remove until audit complete'),
    ('schema_version', 'v3.2.1_prod', 'Current schema version identifier');

-- ── Grant application user access ────────────────────────────────────

CREATE USER IF NOT EXISTS 'novatech_app'@'%' IDENTIFIED WITH mysql_native_password BY 'Pr0d_DB_2024#';
GRANT SELECT, INSERT, UPDATE ON novatech.* TO 'novatech_app'@'%';
FLUSH PRIVILEGES;
