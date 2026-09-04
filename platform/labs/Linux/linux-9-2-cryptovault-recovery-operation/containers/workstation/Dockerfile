FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    openssl \
    gnupg \
    zip \
    && rm -rf /var/lib/apt/lists/*

# ── SSH setup ────────────────────────────────────────────────────────────
RUN mkdir -p /run/sshd

# ── User accounts ────────────────────────────────────────────────────────
# analyst: the student's account
RUN useradd -m -s /bin/bash analyst && \
    echo 'analyst:CV_4n4lyst_2024#' | chpasswd

# mwebb: departed employee (no login, files readable by analyst)
RUN useradd -m -s /bin/bash mwebb

# ── Departed employee home directory ─────────────────────────────────────
# Simulated bash history showing openssl usage
RUN printf 'ls -la\n\
cd /opt/recovery\n\
ls\n\
gpg --version\n\
openssl version\n\
cd ~\n\
ls -la Documents/\n\
openssl enc -aes-256-cbc -pbkdf2 -in audit_report_q4.txt -out audit_backup.enc\n\
ls -la audit_backup.enc\n\
mv audit_report_q4.txt /dev/null\n\
shred -u audit_report_q4.txt\n\
cp audit_backup.enc /opt/recovery/\n\
history -c\n' > /home/mwebb/.bash_history

# Employee record
RUN printf 'CryptoVault Solutions. Employee Record\n\
=============================================\n\
Name:           Marcus Webb\n\
Employee ID:    EMP-4471\n\
Department:     Security Consulting\n\
Title:          Senior Security Consultant\n\
Hire Date:      2019-06-15\n\
Manager:        Diana Reeves\n\
Office:         Austin HQ, Suite 400\n\
Email:          mwebb@cryptovault-solutions.com\n\
Phone:          (512) 555-0187\n\
Status:         SEPARATED (2026-02-25)\n\
Separation:     Voluntary resignation\n\
Exit Interview:  Declined\n\
Equipment:      Laptop reimaged, badge returned\n\
Notes:          Had active projects at time of departure.\n\
                Encrypted backups remain on analyst workstation.\n\
                Recovery approved by Diana Reeves (DIR-OPS).\n' > /home/mwebb/employee-record.txt

# Desktop sticky note
RUN mkdir -p /home/mwebb/Desktop && \
    printf 'Reminder to self:\n\
- Use company standard recovery phrase for all encrypted backups\n\
- Passphrase format is in the policy docs (check /etc/company-policy/)\n\
- Remember to update employee record if ID changes\n\
- Audit report due to Diana by end of November\n' > /home/mwebb/Desktop/sticky_note.txt

# Misc files in home directory (realistic clutter)
RUN mkdir -p /home/mwebb/Documents /home/mwebb/Downloads && \
    printf 'CryptoVault Solutions - Team Meeting Notes\n\
Date: October 15, 2025\n\
Attendees: Diana Reeves, Marcus Webb, Sarah Lin, Tom Greco\n\n\
Agenda:\n\
1. Q4 audit planning\n\
2. New client onboarding\n\
3. Tool license renewals\n\n\
Notes:\n\
- Marcus to lead Q4 internal audit\n\
- Audit scope: network security, access controls, data protection\n\
- Target completion: November 30, 2025\n\
- Diana to provide audit template from shared drive\n' > /home/mwebb/Documents/meeting_notes_oct15.txt && \
    printf 'CryptoVault Solutions - Project Tracker\n\
======================================\n\
Active Projects:\n\
  [DONE] External pentest - Pinnacle Energy (Sep 2025)\n\
  [DONE] Compliance review - Harbor Medical (Oct 2025)\n\
  [WIP]  Internal security audit Q4 (Nov 2025)\n\
  [TODO] New employee security training update\n\n\
Completed Certifications:\n\
  CISSP (2020), GPEN (2021), GCIH (2023)\n' > /home/mwebb/Documents/project_tracker.txt && \
    printf '# Nmap Quick Reference\n\
nmap -sS -sV -p- <target>\n\
nmap -sU --top-ports 100 <target>\n\
nmap --script vuln <target>\n\
nmap -sn 10.0.0.0/24\n' > /home/mwebb/Documents/nmap_cheatsheet.txt

# ── Company encryption policy ───────────────────────────────────────────
RUN mkdir -p /etc/company-policy && \
    printf 'CryptoVault Solutions. Encryption Standard (POL-SEC-007)\n\
================================================================\n\
Effective Date: January 1, 2023\n\
Last Reviewed: July 15, 2025\n\
Approved By: Diana Reeves, Director of Operations\n\n\
1. PURPOSE\n\
   This policy defines the standard encryption methods and passphrase\n\
   construction rules for protecting sensitive company data.\n\n\
2. ENCRYPTION TOOLS\n\
   Approved tools for file encryption:\n\
   - openssl enc (symmetric, AES-256-CBC with PBKDF2)\n\
   - GPG (asymmetric, for external communications only)\n\n\
   For internal backups and archives, use openssl enc with AES-256-CBC.\n\
   Always use the -pbkdf2 flag for key derivation.\n\n\
3. PASSPHRASE CONSTRUCTION\n\
   All encrypted backups MUST use the company standard passphrase format:\n\n\
     {Company_Prefix}-{Employee_ID}-{Year}\n\n\
   Where:\n\
   - Company_Prefix: CryptoVault (case-sensitive, no spaces)\n\
   - Employee_ID: The employee'"'"'s ID from their personnel record (format: EMP-XXXX)\n\
   - Year: The four-digit year the backup was created\n\n\
   Example: CryptoVault-EMP-1234-2023\n\n\
4. KEY RECOVERY\n\
   If an employee departs, their encrypted files can be recovered by\n\
   reconstructing the passphrase from the employee record and this policy.\n\
   Recovery requests must be approved by a Director-level manager.\n\n\
5. EXCEPTIONS\n\
   Personal files (not company data) may use personal passphrases.\n\
   GPG-encrypted files use individual keypairs and are NOT recoverable\n\
   through this process.\n\n\
6. COMPLIANCE\n\
   Violation of this policy may result in disciplinary action. All\n\
   encryption passphrases must follow this standard without exception\n\
   for company data.\n' > /etc/company-policy/encryption-standard.txt

# ── Recovery directory (shared encrypted archives) ───────────────────────
RUN mkdir -p /opt/recovery

# ── Analyst home directory (student's starting point) ────────────────────
RUN printf 'Welcome to the CryptoVault Solutions Analyst Workstation\n\
=======================================================\n\n\
You have been assigned to recover encrypted backup files\n\
belonging to Marcus Webb (departed employee).\n\n\
Recovery Request:\n\
  Authorized by: Diana Reeves, Director of Operations\n\
  Date: March 1, 2026\n\
  Scope: Locate and decrypt the Q4 internal audit report\n\n\
Marcus'"'"'s files are in /home/mwebb/ and /opt/recovery/.\n\
The company encryption recovery procedure is documented in\n\
/etc/company-policy/.\n\n\
Do NOT attempt to brute force encryption. Follow the standard\n\
recovery procedure.\n' > /home/analyst/README.txt

# ── Generate encrypted files at build time ───────────────────────────────
COPY setup-crypto.sh /tmp/setup-crypto.sh
RUN chmod +x /tmp/setup-crypto.sh && /tmp/setup-crypto.sh && rm /tmp/setup-crypto.sh

# ── Final permissions ────────────────────────────────────────────────────
RUN chown -R mwebb:mwebb /home/mwebb && \
    chmod 755 /home/mwebb && \
    chmod -R a+r /home/mwebb && \
    chmod a+x /home/mwebb /home/mwebb/Documents /home/mwebb/Downloads /home/mwebb/Desktop && \
    chown -R analyst:analyst /home/analyst

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 22

CMD ["/start.sh"]
