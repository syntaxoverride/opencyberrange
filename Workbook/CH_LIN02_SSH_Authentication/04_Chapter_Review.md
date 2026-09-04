# Chapter L2: Review

## What You Learned

Across three labs, you moved from your first authenticated SSH login to deep file system exploration on a production server. Each lab built on the previous one, expanding your access and the scope of your discoveries.

In Exercise L2.1, you authenticated to an SSH server and learned that the login process itself reveals information. The Message of the Day (MOTD) banner disclosed the operating system version, hostname, and server role; all of which an attacker uses to plan further exploitation. A simple login gave you intelligence that no external scan could provide.

In Exercise L2.2, you enumerated the logged-in user's identity, group memberships, and sudo privileges. You discovered that a single employee account had unrestricted root access through sudo, along with plaintext database credentials and SSH keys for lateral movement. Post-authentication enumeration transformed a basic shell into a map of the entire system's access controls.

In Exercise L2.3, you moved beyond the home directory into the web application's file system. Using `find` and `grep`, you located configuration files, environment variables, and forgotten backup files; each containing credentials for databases, APIs, and mail servers. File system exploration revealed that a web server's most sensitive data lives not in user accounts but in the application directories that serve production traffic.

## The Progression You Followed

```mermaid
graph LR
    A[L2.1 SSH Login] --> B[L2.2 User Discovery]
    B --> C[L2.3 File Discovery]
    C --> D[Chapter L3]

    A; "MOTD\nAnalysis" --> B
    B; "Privilege\nEscalation" --> C
    C; "Credential\nHarvesting" --> D
```

| Exercise | Focus | Key Finding |
|-----|-------|-------------|
| L2.1 | SSH login and MOTD analysis | Server identity and OS version disclosed in banner |
| L2.2 | User enumeration and privilege check | Unrestricted sudo access and SSH keys for lateral movement |
| L2.3 | File system exploration | Database credentials, API keys, and backup files in web directories |

## Self-Assessment

Answer each question from memory before checking the answer key at the bottom of this page.

**1. What command reveals your current username on a Linux system?**

> &nbsp;

**2. What does the `id` command display that `whoami` does not?**

> &nbsp;

**3. What sudo output indicates unrestricted root access?**

> &nbsp;

**4. Why is `2>/dev/null` appended to `find` commands during penetration testing?**

> &nbsp;

**5. Name two types of files commonly found in `/var/www/html/` that contain credentials.**

> &nbsp;

**6. What does `APP_DEBUG=true` in a production `.env` file mean for an attacker?**

> &nbsp;

**7. How does an SSH private key in a user's `.ssh/` directory enable lateral movement?**

> &nbsp;

**8. What `grep` flags allow a recursive, case-insensitive search for the word "password" across a directory?**

> &nbsp;

## Command Cheat Sheet

| Command | Purpose | Exercise |
|---------|---------|-----|
| `ssh user@<target_ip>` | Connect to target via SSH | L2.1 |
| `hostname` | Display the system hostname | L2.1 |
| `cat /etc/os-release` | Show OS version details | L2.1 |
| `uname -a` | Display kernel version | L2.1 |
| `whoami` | Display current username | L2.2 |
| `id` | Show UID, GID, and group memberships | L2.2 |
| `groups` | List group memberships | L2.2 |
| `sudo -l` | List allowed sudo commands | L2.2 |
| `ls -la` | List all files including hidden | L2.2 |
| `cat ~/.bash_history` | Read command history | L2.2 |
| `cat ~/.ssh/known_hosts` | Show previously connected hosts | L2.2 |
| `find / -name "*.conf" 2>/dev/null` | Search for configuration files | L2.3 |
| `find / -name ".env" 2>/dev/null` | Search for environment files | L2.3 |
| `find / -name "*.bak" 2>/dev/null` | Search for backup files | L2.3 |
| `grep -ri "password" /path/ 2>/dev/null` | Search for password strings | L2.3 |
| `exit` | Disconnect SSH session | All |

## Connect the Dots: What Comes Next

You now know how to authenticate, enumerate users, and discover files. Chapter L3; **SSH Post-Exploitation**: takes you further into the system. You will execute commands to gather network configuration and running processes, analyze shell history for operational intelligence, and escalate privileges from a standard user to root. The credentials and sudo access you discovered in Chapter L2 become the tools you wield in Chapter L3.

---

## Self-Assessment Answer Key

**1.** The `whoami` command displays the current username.

**2.** The `id` command displays the numeric UID, primary GID, and all group memberships, while `whoami` only shows the username.

**3.** The output `(ALL : ALL) ALL` indicates the user can run any command as any user, granting unrestricted root access.

**4.** The `2>/dev/null` redirect suppresses "Permission denied" errors from directories the user cannot access, keeping the output clean and focused on accessible results.

**5.** Configuration files (`config.php`) and environment files (`.env`) both commonly contain database credentials, API keys, and service passwords in plaintext.

**6.** Debug mode causes the application to display detailed error messages, stack traces, and sometimes environment variables in the browser, allowing an attacker to harvest credentials and internal paths by triggering application errors.

**7.** The private key can authenticate to any system where the corresponding public key is stored in `authorized_keys`. Combined with `known_hosts` entries that reveal previously connected servers, the attacker can move to other systems without needing additional passwords.

**8.** The flags `-r` (recursive) and `-i` (case-insensitive) enable a broad search: `grep -ri "password" /path/`.
