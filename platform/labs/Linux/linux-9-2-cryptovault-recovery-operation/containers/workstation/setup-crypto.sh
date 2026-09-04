#!/bin/bash
# Build-time script: generates encrypted files for the exercise
# Runs during Docker build to create both real and decoy encrypted archives

set -e

MWEBB_HOME="/home/mwebb"
RECOVERY_DIR="/opt/recovery"

# ── Create the real audit report (to be encrypted with openssl) ──────────
AUDIT_REPORT=$(cat <<'REPORT'
CryptoVault Solutions | Internal Security Audit Report
=======================================================
Audit ID: CVS-AUDIT-2025-Q4
Auditor: Marcus Webb, Senior Consultant
Date: November 2025
Classification: CONFIDENTIAL

Executive Summary:
This report documents findings from the Q4 internal security audit of
CryptoVault Solutions' infrastructure and processes. The audit covered
network security, access controls, data protection, and incident response
procedures.

Critical Finding #1: Encryption Key Management
Several team members are using the company-standard passphrase format
for encrypting sensitive files. While the format provides a baseline,
the predictable structure means anyone with access to employee records
and the encryption policy can reconstruct passphrases. Recommend
migrating to certificate-based encryption or a centralized key
management system.

Critical Finding #2: Shared Workstation Access
The analyst workstation allows cross-user file access. Home directories
are world-readable, which means any analyst can read another's files
including bash history. This was how this audit itself was initiated.

Critical Finding #3: Data Retention
Legacy client assessment reports are retained beyond the 2-year policy
window. 14 reports from 2022 are still on the shared drive.

Assessment Finding: OCR{r3c0v3ry_pr0c3dur3_f0ll0w3d}

Recommendations:
1. Deploy HashiCorp Vault for encryption key management
2. Restrict home directory permissions to 700
3. Implement automated data retention enforcement
4. Conduct quarterly access reviews for shared resources

Report Status: DRAFT | Pending review by Diana Reeves
REPORT
)

# Encrypt the audit report with the company-standard passphrase
echo "$AUDIT_REPORT" | openssl enc -aes-256-cbc -pbkdf2 \
    -pass pass:CryptoVault-EMP-4471-2025 \
    -out "${MWEBB_HOME}/audit_backup.enc"

# ── Create decoy encrypted files (GPG: truly uncrackable) ──────────────
# These use strong random passphrases that cannot be derived

echo "Marcus Webb - personal notes 2025" | gpg --batch --yes --passphrase "$(openssl rand -hex 32)" \
    --symmetric --cipher-algo AES256 -o "${RECOVERY_DIR}/personal_notes.gpg" 2>/dev/null

echo "Client assessment template v3" | gpg --batch --yes --passphrase "$(openssl rand -hex 32)" \
    --symmetric --cipher-algo AES256 -o "${RECOVERY_DIR}/assessment_template.gpg" 2>/dev/null

echo "Travel expense report Q3 2025" | gpg --batch --yes --passphrase "$(openssl rand -hex 32)" \
    --symmetric --cipher-algo AES256 -o "${RECOVERY_DIR}/expenses_q3.gpg" 2>/dev/null

# Create a decoy ZIP with strong password
echo "Old project files" > /tmp/old_project.txt
zip -j -P "$(openssl rand -hex 32)" "${RECOVERY_DIR}/old_projects.zip" /tmp/old_project.txt >/dev/null 2>&1
rm /tmp/old_project.txt

# Create another openssl file with a DIFFERENT passphrase (not derivable)
echo "Decoy: This is not the file you are looking for." | openssl enc -aes-256-cbc -pbkdf2 \
    -pass pass:"$(openssl rand -hex 16)" \
    -out "${RECOVERY_DIR}/client_data_backup.enc"

# ── Set permissions ──────────────────────────────────────────────────────
chown -R mwebb:mwebb "${MWEBB_HOME}"
chmod -R 755 "${MWEBB_HOME}"
chmod 644 "${MWEBB_HOME}/audit_backup.enc"
chmod 755 "${RECOVERY_DIR}"
chmod 644 "${RECOVERY_DIR}"/*

echo "[setup] Encrypted files created successfully"
