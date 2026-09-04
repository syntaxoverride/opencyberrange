-- MedCore Health Systems. Database Initialization

USE medcore;

-- ── Users table (for SQL injection target) ────────────────────────────
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user'
);

INSERT INTO users (username, password, email, role) VALUES
    ('admin', 'M3dC0r3_Adm1n#', 'admin@medcore-health.com', 'admin'),
    ('sokafor', 'CISO_Acc3ss_2025!', 'sokafor@medcore-health.com', 'admin'),
    ('ktran', 'CTO_Portal_08#', 'ktran@medcore-health.com', 'admin'),
    ('jliu', 'Clin1cal_R3v13w#', 'jliu@medcore-health.com', 'provider'),
    ('msantos', 'Eng_Dash_2025!', 'msantos@medcore-health.com', 'engineer');

-- ── Audit tokens table ────────────────────────────────────────────────
CREATE TABLE audit_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    value VARCHAR(100) NOT NULL
);

INSERT INTO audit_tokens (name, value) VALUES
    ('db_health_check', 'healthy_2025Q1'),
    ('backup_verification', 'bkp_verified_0315'),
    ('assessment', 'd4t4b4s3'),
    ('schema_version', 'v5.2.0_prod');

-- ── System config table (contains SSH credentials for internal server) ─
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(100) NOT NULL,
    value VARCHAR(200) NOT NULL,
    description VARCHAR(200)
);

INSERT INTO system_config (key_name, value, description) VALUES
    ('APP_VERSION', '5.2.0', 'Current application version'),
    ('FHIR_ENDPOINT', 'https://fhir.medcore-health.com/r4', 'FHIR API endpoint'),
    ('PROC_SERVER_HOST', 'medcore-proc', 'Internal processing server hostname'),
    ('PROC_SSH_USER', 'svcproc', 'SSH username for processing server'),
    ('PROC_SSH_PASS', 'Pr0c_SSH_2025#', 'SSH password for processing server'),
    ('PROC_DATA_DIR', '/opt/medcore/data', 'Data directory on processing server'),
    ('AUDIT_RETENTION_DAYS', '90', 'Audit log retention period');

-- ── Application user (limited SELECT on medcore) ──────────────────────
CREATE USER IF NOT EXISTS 'mdc_app'@'%' IDENTIFIED WITH mysql_native_password BY 'Mdc_App_2025#';
GRANT SELECT ON medcore.users TO 'mdc_app'@'%';
FLUSH PRIVILEGES;

-- ── Admin user (SELECT on all tables) ─────────────────────────────────
CREATE USER IF NOT EXISTS 'mdc_admin'@'%' IDENTIFIED WITH mysql_native_password BY 'Mdc_DB_Pr0d#2025';
GRANT SELECT ON medcore.* TO 'mdc_admin'@'%';
FLUSH PRIVILEGES;
