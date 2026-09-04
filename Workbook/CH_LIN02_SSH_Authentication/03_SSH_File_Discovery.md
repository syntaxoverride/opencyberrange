# Exercise L2.3: SSH File Discovery

## Before You Begin

- Confirm your VPN connection to the lab environment is active
- Open a terminal window with SSH client available
- Complete Exercises L2.1 and L2.2 before starting

## Scenario

The **FinanceCorp** penetration test is progressing. **James Mitchell** has provided credentials for a web administrator account: `webadmin:WebServer2024#`. James wants to understand what sensitive data an attacker could reach through a compromised web administrator account, particularly within the web application directories.

## Your Objectives

- Authenticate to the target as `webadmin` using SSH
- Navigate beyond the home directory to `/var/www/html/`
- Use the `find` command to locate sensitive configuration files and backups
- Extract database credentials from application configuration files
- Discover environment variable files containing secrets

---

## Background: File System Exploration Beyond Home

In Exercise L2.2, you explored the home directory and found credentials and SSH keys. But Linux systems store their most valuable data in application directories, configuration paths, and temporary locations far from any user's home folder.

Web applications are especially rich targets. A typical web server stores its files under `/var/www/html/`, and those files often contain:

- **Configuration files** (`config.php`, `settings.py`); database connection strings with plaintext passwords
- **Environment files** (`.env`); API keys, secret tokens, and service credentials
- **Backup files** (`.bak`, `.old`, `.tar.gz`); archived versions of configuration files, sometimes with older credentials
- **Log files**: application errors that reveal internal paths and database queries

A penetration tester who limits exploration to the home directory misses the majority of actionable findings on a web server.

## Tool Primer: The `find` Command

The `find` command searches the file system for files matching specified criteria. For penetration testing, it is the primary tool for locating sensitive files across an entire system.

**Basic syntax:**

```bash
find <starting_path> [options] [expression]
```

**Key flags:**

| Flag | Purpose |
|------|---------|
| `-name` | Match by filename (case-sensitive) |
| `-iname` | Match by filename (case-insensitive) |
| `-type f` | Match regular files only |
| `-type d` | Match directories only |
| `-user` | Match by file owner |
| `2>/dev/null` | Suppress permission denied errors |

The `2>/dev/null` redirect is essential. Without it, `find` floods your terminal with "Permission denied" errors for every directory you cannot access, burying the actual results.

---

## Walkthrough

### Step 1: Launch the Exercise

Navigate to **Exercises** then **Linux** then **Level 2**. Locate Exercise L2.3, click **Launch**, and wait for the status to show **Running**. Note the **target IP** displayed on the lab panel.

### Step 2: Authenticate as webadmin

!!! kali "Authenticate as the web administrator"
    Connect to the target with the web administrator credentials. Replace `<target_ip>` with the address shown on the lab panel.

    ```bash
    ssh webadmin@<target_ip>
    ```

    When prompted, enter the password below. A successful login drops you into the `webadmin` home directory on the target.

    ```
    WebServer2024#
    ```

### Step 3: Navigate to the Web Application Root

Verify your identity with `whoami`, then move to the web root. Unlike the previous exercise, your primary targets are outside the home directory.

!!! target "Move to the web root and list files"
    Move to the web server's document root where application files are stored.

    ```
    cd /var/www/html/
    ```

    List all files, including hidden ones:

    ```
    ls -la
    ```

    Review the output. Focus on files that are likely to store credentials or sensitive data.

### Step 5: Search for Configuration Files

!!! target "Find and read configuration files"
    Use the `find` command to locate configuration files across the web directory. The `2>/dev/null` redirect suppresses permission-denied noise.

    ```
    find /var/www/html/ -name "config*" \
      -type f 2>/dev/null
    ```

    Read the discovered `config.php`:

    ```
    <?php
    // Database Configuration
    $db_host = "localhost";
    $db_user = "webapp_admin";
    $db_pass = "W3bApp_S3cur3_2024";
    $db_name = "financecorp_webapp";

    // API Configuration
    $api_key = "fc-api-8a3b2c1d4e5f";
    ?>
    ```

    Record every credential and key found. The database password and API key are reusable against other services.

### Step 6: Locate Environment Files

!!! target "Find and read environment files"
    Search for `.env` files that store application secrets.

    ```
    find /var/www/ -name ".env" \
      -type f 2>/dev/null
    ```

    Read the discovered environment file:

    ```
    cat /var/www/html/.env
    ```

    Expected output:

    ```
    APP_NAME=FinanceCorp Portal
    APP_ENV=production
    APP_KEY=base64:Fc8k3mN7pQ2xR5vB9wY1zA4cE6gH8jL0
    APP_DEBUG=true

    DB_CONNECTION=mysql
    DB_HOST=127.0.0.1
    DB_PORT=3306
    DB_DATABASE=financecorp_portal
    DB_USERNAME=portal_user
    DB_PASSWORD=P0rt4l_Pr0d_2024

    MAIL_HOST=smtp.financecorp.local
    MAIL_USERNAME=noreply@financecorp.local
    MAIL_PASSWORD=M4il_S3rv3r_2024
    ```

    Catalog the database and mail credentials. Note `APP_DEBUG=true`, which means the application leaks detailed errors in production.

### Step 7: Discover Backup Files

!!! target "Find and read backup files"
    Backup files are frequently left in place after updates. Search for common backup extensions.

    ```
    find /var/www/html/ -name "*.bak" -o \
      -name "*.old" -o -name "*.backup" \
      2>/dev/null
    ```

    Read any discovered backup files:

    ```
    cat /var/www/html/config.php.bak
    ```

    Backup files often contain older credentials that may still be valid on other systems.

### Step 8: Search for Credentials with grep

!!! target "Grep recursively for password strings"
    Use `grep` to search for password strings across all files.

    ```
    grep -ri "password" /var/www/html/ \
      2>/dev/null
    ```

    The `-r` flag searches recursively and `-i` makes the search case-insensitive. Each match points to another file worth reading in full.

### Step 9: Capture the Flag

!!! target "Locate and read the flag"
    Locate the flag for this exercise.

    ```
    find /var/www/html/ -name "*flag*" \
      -type f 2>/dev/null
    ```

    Read the flag file:

    ```
    cat /var/www/html/flag.txt
    ```

    Expected flag format: `OCR{...}`. Record the value for submission.

### Record Your Findings

> **Web Application Files**
>
> | File Path | Contents |
> |-----------|----------|
> | `/var/www/html/config.php` | __________ |
> | `/var/www/html/.env` | __________ |
> | __________ | __________ |
>
> **Discovered Credentials**
>
> | Source | Username | Password | Service |
> |--------|----------|----------|---------|
> | config.php | __________ | __________ | __________ |
> | .env (DB) | __________ | __________ | __________ |
> | .env (Mail) | __________ | __________ | __________ |
> | config.php.bak | __________ | __________ | __________ |
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** `OCR{____________}`

### Step 10: Record the Flag

Copy the flag (it follows the `OCR{...}` format) and submit it on the lab platform in the designated field to complete Exercise L2.3.

!!! target "Close the SSH session"
    Disconnect from the target by running `exit`.

    ```
    exit
    ```

---

## Analysis Questions

**1. Why are web application directories a higher-value target than home directories on a web server?**

??? note "Reveal Answer"

    Web application directories contain the files that power the running application; database connection strings, API keys, mail server credentials, and session secrets. A home directory might contain personal files and SSH keys, but the application directory holds credentials that grant access to databases, third-party services, and other infrastructure components serving all users.

**2. What security risk does leaving backup files (`.bak`, `.old`) in a web-accessible directory create?**

??? note "Reveal Answer"

    Backup files may be served directly by the web server if not explicitly blocked, exposing source code and credentials to anyone who guesses the filename. Older backups may contain previous credentials that were never rotated, granting access to systems the current configuration no longer references.

**3. How does `APP_DEBUG=true` in a production `.env` file compound the risk of credential exposure?**

??? note "Reveal Answer"

    Debug mode causes the application to display detailed error messages including stack traces, database queries, file paths, and sometimes the full contents of environment variables. An attacker who triggers an error; even without shell access; can harvest credentials, internal paths, and infrastructure details directly from the error page displayed in a browser.

---

## Key Takeaways

- **File system exploration must extend beyond the home directory**: web application directories under `/var/www/html/` contain credentials, API keys, and configuration data that represent the highest-value findings on a web server
- **The `find` command is essential for penetration testing**: combining filename patterns with `2>/dev/null` allows efficient searching across directories where partial access restrictions apply
- **Configuration files store credentials in plaintext** by design, making them primary targets during any authenticated file system exploration
- **Environment files (`.env`) centralize secrets**: a single `.env` file often contains database passwords, API keys, mail credentials, and encryption keys all in one location
- **Backup files persist after administrators forget them**: old configurations with outdated credentials remain on disk and are readable by any authenticated user
- **Recursive `grep` for keywords like "password"** is a fast method to locate credential disclosures across thousands of files without reading each one individually
