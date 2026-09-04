-- Stonebridge Capital. Database initialization
-- Creates application user and audit_flags table

CREATE USER IF NOT EXISTS 'sb_app'@'%' IDENTIFIED WITH mysql_native_password BY 'St0n3br1dg3_DB#';
GRANT SELECT ON stonebridge.* TO 'sb_app'@'%';
FLUSH PRIVILEGES;

USE stonebridge;

CREATE TABLE audit_flags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    value VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO audit_flags (name, value) VALUES ('assessment_marker', 'l34k');
