# Pinnacle Legal Group Security Assessment

## Overview
Midterm assessment covering multi-host network enumeration. Students discover three machines on their subnet, enumerate services on each, and collect three flag parts from different protocols and techniques.

**Flag:** `OCR{p1nn4cl3_d1sc0v3ry_3xp0s3d}`

## Target Machines

| Machine | Key Services | Flag Part |
|---------|-------------|-----------|
| Client Portal | HTTP:80 | Part 1: `p1nn4cl3` (on `/notices.html`) |
| Document Server | SMB:445, FTP:2121, SSH:22 | Part 2: `d1sc0v3ry` (FTP anonymous on 2121) |
| Case Management | LDAP:389, SMB:445, RDP:3389, Kerberos:88 | Part 3: `3xp0s3d` (SMB authenticated share) |

## Solution Walkthrough

### Step 1: Host Discovery
Scan the assigned subnet to find all live hosts:
```bash
nmap -sn 10.100.X.0/24
```
Three hosts should respond (IPs are randomized per student).

### Step 2: Service Enumeration
Full port scan each discovered host to identify roles:
```bash
nmap -sV -p- <host1> <host2> <host3>
```

Expected service signatures:
- **Client Portal**: Port 80 (HTTP/Apache)
- **Document Server**: Ports 22 (SSH), 445 (SMB), 2121 (FTP)
- **Case Management**: Ports 88, 389 (LDAP), 445 (SMB), 3389 (RDP)

### Step 3: Flag Part 1: Web Portal (Passive Recon)
Browse the website on port 80. Navigate through the pages:
- Home page links to About, Team, IT Support, and Notices
- Visit `/notices.html`: read the internal memos
- The "IT Infrastructure Migration" memo contains: `Flag 1: p1nn4cl3`

Also on the website:
- Visit `/helpdesk.html`: the "New Employee; Document Management Access" section lists:
  - **SMB credentials:** `paralegal` / `Summer2024#` (connect to the `cases` share on the document server)
  - **FTP anonymous access:** `anonymous` login, no password (read-only access to `archived-cases` on the document server)

### Step 4: Flag Part 2: Document Server (SMB → FTP breadcrumb)
Use the discovered credentials to access the SMB share:
```bash
smbclient //<docserver_ip>/cases -U paralegal%Summer2024#
smb: \> ls
smb: \> get case-transfer-memo.txt
```

Read the memo; it mentions archived files on a legacy FTP service running on **port 2121** with anonymous access.

Connect to FTP on the non-standard port:
```bash
ftp <docserver_ip> 2121
# Login: anonymous (no password)
ftp> ls
ftp> cd archived-cases
ftp> get flag-part.txt
```

The file contains: `Flag 2: d1sc0v3ry`

It also contains credentials for the case management server:
- **Username:** `attorney`
- **Password:** `CaseFile2024#`
- **Share:** `records`

**Alternative path:** SSH to the document server with `paralegal / Summer2024#`: the home directory contains `archive-notice.txt` which also hints at FTP on port 2121.

### Step 5: Flag Part 3: Case Management (Authenticated SMB)
Use the credentials found in the FTP flag file to access the case management server's SMB share:
```bash
smbclient //<casemgmt_ip>/records -U attorney%CaseFile2024#
smb: \> ls
smb: \> get flag-part.txt
```

The file contains: `Flag 3: 3xp0s3d`

### Step 6: Assemble the Flag
Combine all three parts:
```
OCR{p1nn4cl3_d1sc0v3ry_3xp0s3d}
```

## Common Mistakes
- Not scanning the full port range (missing FTP on 2121)
- Trying to brute force SMB when credentials are on the website
- Not reading all pages on the website (skipping Notices or IT Support)
- Not exploring FTP subdirectories (flag is in `archived-cases/`, not root)
- Not reading the FTP flag file carefully; it contains both Flag 2 and the credentials for Flag 3

## Skills Assessed
- Subnet/host discovery scanning
- Full port range service enumeration
- Passive web reconnaissance (reading site content)
- Authenticated SMB file share access
- FTP anonymous access on non-standard port
- Following breadcrumb trails across multiple services
- Multi-part flag assembly
