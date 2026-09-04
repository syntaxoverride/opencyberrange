-- Meridian Financial Group. Database Initialization
-- Three databases: meridian_compliance, meridian_hr, meridian_finance
-- The application service account (meridian_app) has SELECT on compliance only

-- =========================================================================
-- Database: meridian_compliance (accessible to meridian_app)
-- =========================================================================

CREATE DATABASE IF NOT EXISTS `meridian_compliance`;
USE `meridian_compliance`;

-- ── Data Classifications ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `data_classifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `record_name` varchar(200) NOT NULL,
  `classification` enum('Public','Internal','Confidential','PII') NOT NULL,
  `database_name` varchar(100) DEFAULT NULL,
  `table_name` varchar(100) DEFAULT NULL,
  `retention_years` int DEFAULT NULL,
  `last_review_date` date DEFAULT NULL,
  `reviewed_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `data_classifications` VALUES
(1, 'Marketing Materials', 'Public', NULL, NULL, NULL, '2025-09-15', 'Laura Chen'),
(2, 'Employee Directory', 'Internal', 'meridian_hr', 'employees', 3, '2025-09-15', 'Laura Chen'),
(3, 'Client Account Records', 'PII', 'meridian_finance', 'client_accounts', 7, '2025-09-15', 'Laura Chen'),
(4, 'Transaction History', 'Confidential', 'meridian_finance', 'transactions', 7, '2025-09-15', 'Laura Chen'),
(5, 'Compliance Audit Log', 'Internal', 'meridian_compliance', 'audit_log', 7, '2025-09-15', 'Laura Chen'),
(6, 'PII Export. Q3 Client Report', 'PII', 'meridian_finance', 'client_pii_export', 7, '2025-10-01', 'Jennifer Walsh'),
(7, 'Vendor Payment Records', 'Confidential', 'meridian_finance', 'vendor_payments', 5, '2025-09-15', 'Laura Chen'),
(8, 'Internal Meeting Notes', 'Internal', NULL, NULL, 1, '2025-09-15', 'Laura Chen');

-- ── Compliance Findings ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `compliance_findings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `finding_id` varchar(20) NOT NULL,
  `severity` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL,
  `category` varchar(100) NOT NULL,
  `finding_summary` varchar(500) NOT NULL,
  `finding_detail` text,
  `reported_by` varchar(100) DEFAULT NULL,
  `reported_date` date DEFAULT NULL,
  `status` enum('OPEN','IN_PROGRESS','RESOLVED','CLOSED') NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `compliance_findings` VALUES
(1, 'CF-2025-041', 'LOW', 'Policy Compliance', 'Password expiry notifications not sent to 3 employees', 'Automated email notification system failed for users: sokafor, tbradley, jwalsh. Resolved by updating SMTP relay configuration.', 'Jennifer Walsh', '2025-08-20', 'CLOSED'),
(2, 'CF-2025-042', 'MEDIUM', 'Access Control', 'Former contractor account not disabled within 24-hour SLA', 'Contractor David Kim (dkim@external) retained VPN access for 72 hours after contract termination. Access revoked on 2025-09-05.', 'Laura Chen', '2025-09-03', 'CLOSED'),
(3, 'CF-2025-043', 'HIGH', 'Data Retention', 'PII export file retained beyond retention window', 'The Q3 client PII export (meridian_finance.client_pii_export) was retained 14 days beyond the approved retention window. Data was purged on 2025-10-15.', 'Jennifer Walsh', '2025-10-01', 'RESOLVED'),
(4, 'CF-2025-044', 'MEDIUM', 'Encryption', 'Legacy backup files stored without encryption', 'Pre-migration SQL dumps stored on intranet server in plaintext. Files moved to archive directory pending purge. Risk accepted during 90-day retention window.', 'James Park', '2025-12-15', 'IN_PROGRESS'),
(5, 'CF-2026-001', 'CRITICAL', 'Data Exposure', 'Unprotected backup archive accessible via intranet web server', 'During routine compliance review, legacy backup SQL dump files were found accessible via the intranet web server without authentication. The archive directory containing database exports with application credentials was not restricted after the backup migration. Assessment finding: OCR{d4ta_br34ch_3xp0s3d}', 'Laura Chen', '2026-02-28', 'OPEN');

-- ── Audit Log ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_time` datetime NOT NULL,
  `user` varchar(100) NOT NULL,
  `action` varchar(200) NOT NULL,
  `details` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `audit_log` VALUES
(1, '2025-12-10 02:00:01', 'system', 'DATABASE_EXPORT', 'Automated pre-migration backup completed successfully'),
(2, '2025-12-12 14:23:17', 'jpark', 'MIGRATION_START', 'Database migration initiated for meridian-db'),
(3, '2025-12-12 16:45:33', 'jpark', 'MIGRATION_COMPLETE', 'Database migration completed. All schemas verified.'),
(4, '2026-01-15 09:12:44', 'lchen', 'COMPLIANCE_SCAN', 'Quarterly data classification scan completed. 8 records reviewed.'),
(5, '2026-02-18 11:30:00', 'mtorres', 'BACKUP_MIGRATION', 'Legacy backup files moved to intranet archive directory'),
(6, '2026-02-28 15:45:22', 'lchen', 'FINDING_REPORTED', 'CF-2026-001: Unprotected backup archive identified during compliance review');


-- =========================================================================
-- Database: meridian_hr (NOT accessible to meridian_app)
-- =========================================================================

CREATE DATABASE IF NOT EXISTS `meridian_hr`;
USE `meridian_hr`;

CREATE TABLE IF NOT EXISTS `employees` (
  `id` int NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `email` varchar(200) NOT NULL,
  `department` varchar(100) NOT NULL,
  `title` varchar(200) NOT NULL,
  `hire_date` date NOT NULL,
  `salary` decimal(10,2) DEFAULT NULL,
  `ssn_hash` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `employees` VALUES
(1, 'Robert', 'Whitfield', 'rwhitfield@meridian-financial.com', 'Executive', 'CEO', '1998-03-15', 425000.00, 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'),
(2, 'James', 'Park', 'jpark@meridian-financial.com', 'Information Technology', 'IT Director', '2005-06-01', 185000.00, 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7'),
(3, 'Laura', 'Chen', 'lchen@meridian-financial.com', 'Compliance', 'Chief Compliance Officer', '2010-01-15', 195000.00, 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8'),
(4, 'Sandra', 'Okafor', 'sokafor@meridian-financial.com', 'Advisory', 'VP Wealth Management', '2012-04-20', 210000.00, 'd4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9'),
(5, 'Michael', 'Torres', 'mtorres@meridian-financial.com', 'Information Technology', 'Senior Developer', '2015-08-10', 145000.00, 'e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0'),
(6, 'Angela', 'Price', 'aprice@meridian-financial.com', 'Human Resources', 'HR Manager', '2016-02-14', 120000.00, 'f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1'),
(7, 'David', 'Nakamura', 'dnakamura@meridian-financial.com', 'Information Technology', 'Database Administrator', '2018-11-05', 135000.00, 'a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2'),
(8, 'Rachel', 'Graves', 'rgraves@meridian-financial.com', 'Finance', 'Finance Director', '2014-07-22', 175000.00, 'b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3'),
(9, 'Thomas', 'Bradley', 'tbradley@meridian-financial.com', 'Information Technology', 'Network Engineer', '2019-03-18', 125000.00, 'c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4'),
(10, 'Jennifer', 'Walsh', 'jwalsh@meridian-financial.com', 'Compliance', 'Compliance Analyst', '2020-09-01', 95000.00, 'd0e1f2a3b4c5d6a7b8c9d0e1f2a3b4c5');


-- =========================================================================
-- Database: meridian_finance (NOT accessible to meridian_app)
-- =========================================================================

CREATE DATABASE IF NOT EXISTS `meridian_finance`;
USE `meridian_finance`;

CREATE TABLE IF NOT EXISTS `client_accounts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `client_name` varchar(200) NOT NULL,
  `account_number` varchar(20) NOT NULL,
  `account_type` enum('Individual','Joint','Trust','Corporate') NOT NULL,
  `balance` decimal(15,2) DEFAULT NULL,
  `advisor_id` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `client_accounts` VALUES
(1, 'Harrison Trust', 'MFG-2024-00147', 'Trust', 4250000.00, 4),
(2, 'Whitaker Family', 'MFG-2024-00203', 'Joint', 1850000.00, 4),
(3, 'Piedmont Holdings LLC', 'MFG-2024-00089', 'Corporate', 8700000.00, 4),
(4, 'Elizabeth Dunn', 'MFG-2024-00312', 'Individual', 725000.00, 4),
(5, 'Campbell Revocable Trust', 'MFG-2024-00455', 'Trust', 3100000.00, 4);

CREATE TABLE IF NOT EXISTS `transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_id` int NOT NULL,
  `transaction_date` datetime NOT NULL,
  `type` enum('Buy','Sell','Deposit','Withdrawal','Fee') NOT NULL,
  `amount` decimal(15,2) NOT NULL,
  `description` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `transactions` VALUES
(1, 1, '2025-11-15 10:30:00', 'Buy', 250000.00, 'VTI - Vanguard Total Stock Market ETF'),
(2, 1, '2025-11-15 10:30:00', 'Buy', 150000.00, 'BND - Vanguard Total Bond Market ETF'),
(3, 2, '2025-12-01 09:15:00', 'Deposit', 50000.00, 'Annual contribution'),
(4, 3, '2025-12-10 14:00:00', 'Fee', 8700.00, 'Q4 advisory fee (0.1%)'),
(5, 4, '2026-01-05 11:45:00', 'Sell', 25000.00, 'AAPL - partial position liquidation');


-- =========================================================================
-- Application service account. SELECT on meridian_compliance only
-- =========================================================================

CREATE USER IF NOT EXISTS 'meridian_app'@'%' IDENTIFIED WITH mysql_native_password BY 'M3r1d14n_App_2024#';
GRANT SELECT ON meridian_compliance.* TO 'meridian_app'@'%';
FLUSH PRIVILEGES;
