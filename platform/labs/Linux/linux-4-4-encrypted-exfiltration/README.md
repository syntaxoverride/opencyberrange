# Obsidian Analytics: Encrypted Exfiltration

## Overview

Students demonstrate post-exploitation exfiltration techniques on an Obsidian Analytics server. Sensitive data has been concealed using three different methods: base64 encoding, GPG symmetric encryption, and hex encoding. Students must locate, decode, and decrypt each artifact to recover three flag tokens.

## Architecture

```
┌─────────────┐                     ┌──────────────┐
│   Student    │ ──── SSH:22 ─────▶ │    target     │
│   (Kali VM)  │                    │  (obsidian)   │
└─────────────┘                     └──────────────┘
                                     User: operator
                                     Goal: exfiltrate
```

## Data Concealment Map

```
operator (initial access via SSH)
    │
    ├── Token 1: /var/backups/obsidian/export.b64
    │       └── Base64-encoded file → decode to find "assessment_marker: 3ncrypt"
    │
    ├── Token 2: /opt/obsidian/data/archive.gpg
    │       └── GPG symmetric encryption (AES256)
    │       └── Password found in /home/operator/.bash_history
    │       └── Decrypts to reveal "marker_value=d3c0d3"
    │
    └── Token 3: /opt/obsidian/.cache/.data_store
            └── Hex-encoded string → decode with xxd -r -p → "3xf1l"
```

## Solution Walkthrough

### Step 1: Connect as Operator

```bash
ssh operator@<target_ip>
# Password: 0bs1d14n_0ps#
```

### Step 2: Decode the Base64 Export (Token 1)

```bash
base64 -d /var/backups/obsidian/export.b64
# Look for the line: assessment_marker: 3ncrypt
```

Token 1: `3ncrypt`

### Step 3: Find GPG Passphrase in Bash History

```bash
cat ~/.bash_history
# Reveals: gpg --batch --passphrase '0bs1d14n_Vault#' -d /opt/obsidian/data/archive.gpg
```

### Step 4: Decrypt the GPG Archive (Token 2)

```bash
gpg --batch --passphrase '0bs1d14n_Vault#' -d /opt/obsidian/data/archive.gpg
# Look for the line: marker_value=d3c0d3
```

Token 2: `d3c0d3`

### Step 5: Decode the Hex Dotfile (Token 3)

```bash
cat /opt/obsidian/.cache/.data_store | xxd -r -p
# Output: 3xf1l
```

Token 3: `3xf1l`

### Step 6: Assemble the Flag

Combine the three tokens: `OCR{3ncrypt_d3c0d3_3xf1l}`

## Common Mistakes

- **Skipping hidden directories.** Students may not find `.cache` under `/opt/obsidian/` without using `ls -la` or `find` with dotfile awareness.
- **Not checking bash history.** The GPG passphrase is only discoverable through `.bash_history`: students who skip history analysis will be stuck on the encrypted archive.
- **Not recognizing hex encoding.** The `.data_store` file contains a plain hex string that looks like random data. Students need to recognize it as hex and know how to decode it with `xxd -r -p`.
- **Trying to brute-force the GPG password.** The passphrase is complex enough that brute-forcing is impractical; the intended path is through history forensics.

## Defensive Recommendations

- Never leave decryption commands with passwords in shell history (configure HISTCONTROL or use ephemeral credential stores)
- Avoid storing sensitive exports in predictable backup directories
- Use proper secrets management for encryption keys (HashiCorp Vault, AWS KMS)
- Implement file integrity monitoring to detect unauthorized data access
- Apply the principle of least privilege; operators should not have sudo NOPASSWD access
