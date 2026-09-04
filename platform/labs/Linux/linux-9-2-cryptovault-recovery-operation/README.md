# CryptoVault. Recovery Operation

## Overview

Students recover an encrypted audit report from a departed employee's workstation by following the company's documented encryption recovery procedure. The exercise reinforces encryption concepts (symmetric vs. asymmetric), key management weaknesses, data recovery procedures, and policy-based passphrase construction.

## Architecture

```
┌─────────────┐                     ┌──────────────────┐
│   Student    │ ──── SSH:22 ─────▶ │  workstation      │
│   (Kali VM)  │                    │  (analyst account) │
│              │                    │                    │
└─────────────┘                     │  /home/mwebb/      │ ← departed employee files
                                    │  /opt/recovery/    │ ← encrypted archives
                                    │  /etc/company-     │ ← encryption policy
                                    │       policy/      │
                                    └──────────────────┘
```

## Solution Walkthrough

### Step 1: Explore the Workstation

```bash
ssh analyst@<workstation_ip>
# Password: CV_4n4lyst_2024#

cat ~/README.txt
# Recovery task description, points to /home/mwebb/ and /etc/company-policy/
```

### Step 2: Enumerate Departed Employee's Files

```bash
ls -la /home/mwebb/
# Desktop/  Documents/  Downloads/  .bash_history  audit_backup.enc  employee-record.txt

ls /home/mwebb/Desktop/
# sticky_note.txt

ls /home/mwebb/Documents/
# meeting_notes_oct15.txt  nmap_cheatsheet.txt  project_tracker.txt

ls /opt/recovery/
# assessment_template.gpg  client_data_backup.enc  expenses_q3.gpg
# old_projects.zip  personal_notes.gpg
```

### Step 3: Identify Encryption Method

```bash
cat /home/mwebb/.bash_history
# Shows: openssl enc -aes-256-cbc -pbkdf2 -in audit_report_q4.txt -out audit_backup.enc
# Key insight: Marcus used openssl, not GPG
```

### Step 4: Find the Recovery Procedure

```bash
cat /home/mwebb/Desktop/sticky_note.txt
# References "company standard recovery phrase" and /etc/company-policy/

cat /etc/company-policy/encryption-standard.txt
# Passphrase format: {Company_Prefix}-{Employee_ID}-{Year}
# Company_Prefix = CryptoVault
```

### Step 5: Get Employee ID

```bash
cat /home/mwebb/employee-record.txt
# Employee ID: EMP-4471
```

### Step 6: Reconstruct Passphrase and Decrypt

```bash
# Passphrase: CryptoVault-EMP-4471-2025
# (Year is 2025 because bash_history shows the encryption happened in 2025)

openssl enc -aes-256-cbc -d -pbkdf2 \
    -in /home/mwebb/audit_backup.enc \
    -pass pass:CryptoVault-EMP-4471-2025

# Output: Internal audit report containing OCR{r3c0v3ry_pr0c3dur3_f0ll0w3d}
```

## Red Herrings

- **GPG files in /opt/recovery/**: Encrypted with random passphrases. Cannot be recovered through the company procedure (policy states GPG uses individual keypairs, not the standard format).
- **client_data_backup.enc**: An openssl file but encrypted with a non-standard passphrase. Students who try the standard format will get a decryption error. this teaches that not all .enc files follow the policy.
- **old_projects.zip**: Password-protected ZIP with a random password. Not recoverable.

## Common Mistakes

- **Trying to brute force the GPG files.** The policy explicitly states GPG uses individual keypairs not covered by the recovery procedure.
- **Using the wrong year.** The bash_history shows the encryption was done in 2025, not 2026. Some students may use the current year.
- **Not reading the sticky note.** It is the breadcrumb that points to the policy directory.
- **Trying files in /opt/recovery/ first.** The target file (audit_backup.enc) is in /home/mwebb/, not /opt/recovery/.

## Defensive Recommendations

- Predictable passphrase formats are a key management weakness. Use a centralized key management system
- Restrict home directory permissions (chmod 700) to prevent cross-user file access
- Implement automated encryption key escrow rather than policy-based recovery
- Clean bash history of sensitive commands before account deprovisioning
- Use asymmetric encryption for data that may need recovery (encrypt to a recovery key)
