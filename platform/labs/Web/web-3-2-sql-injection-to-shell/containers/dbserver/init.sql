-- Vertex Healthcare. Portal Database Initialization

USE vertex_portal;

-- ── Users table ─────────────────────────────────────────────────────
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL
);

INSERT INTO users (username, password, email) VALUES
    ('admin', 'Adm1n_V3rt3x#', 'admin@vertexhealthcare.com'),
    ('jnguyen', 'Clinic_User_08#', 'jnguyen@vertexhealthcare.com'),
    ('mthompson', 'Provider_Acc3ss!', 'mthompson@vertexhealthcare.com');

-- ── Audit flags table ───────────────────────────────────────────────
CREATE TABLE audit_flags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    value VARCHAR(100) NOT NULL
);

INSERT INTO audit_flags (name, value) VALUES
    ('db_health_check', 'healthy_2025Q1'),
    ('backup_verification', 'bkp_verified_0228'),
    ('assessment', '3xtr4ct'),
    ('schema_version', 'v4.1.0_prod');

-- ── Application user (limited SELECT on vertex_portal) ──────────────
CREATE USER IF NOT EXISTS 'vtx_app'@'%' IDENTIFIED WITH mysql_native_password BY 'Vtx_App_2024#';
GRANT SELECT ON vertex_portal.users TO 'vtx_app'@'%';
FLUSH PRIVILEGES;

-- ── Admin user (SELECT on all databases) ────────────────────────────
CREATE USER IF NOT EXISTS 'vtx_admin'@'%' IDENTIFIED WITH mysql_native_password BY 'Vtx_DB_R00t#';
GRANT SELECT ON *.* TO 'vtx_admin'@'%';
FLUSH PRIVILEGES;
