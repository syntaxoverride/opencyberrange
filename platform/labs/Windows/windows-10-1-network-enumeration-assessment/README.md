# Midterm Lab: FinanceCorp Network Enumeration Assessment

## Overview

This lab is a midterm assessment covering passive and active scanning. Students must discover three hosts on their assigned subnet (IPs are **randomized per student**), identify each machine by its services, and collect three flag parts to form the complete flag **OCR{m1dt3rm_n3tw0rk_3num}**.

## Learning Objectives

- Discover live hosts using subnet scanning (`nmap -sn`)
- Identify hosts by open ports and services (web portal, file server, domain controller)
- Apply passive recon (web source, robots.txt, HTTP content) and active recon (port scan, version/OS detection, SMB enumeration)
- Assemble the flag from three parts: `OCR{m1dt3rm_n3tw0rk_3num}`

## Solution Walkthrough (Instructor)

IPs vary by student; the solution is described by **role** (identified by port scan), not by fixed IP.

### Step 1: Discover hosts

```bash
nmap -sn 10.100.X.0/24
```

Replace `X` with the student's subnet (from the lab panel). Three hosts will be up; their last octets are randomized (e.g. .17, .83, .201).

### Step 2: Port-scan each host

Scan each discovered IP to identify roles:

| Role         | Key ports        | Identification                    |
|-------------|------------------|-----------------------------------|
| Web portal  | 80, 8080         | HTTP only                         |
| File server | 21, 445, 2222     | FTP, SMB, SSH (non-standard port)  |
| Domain controller | 88, 139, 389, 445, 3389 | Kerberos, NetBIOS, LDAP, SMB, RDP |

Example:

```bash
nmap -sV -p- <ip1>
nmap -sV -p- <ip2>
nmap -sV -p- <ip3>
```

### Step 3: Flag part 1 (web portal)

- Browse to `http://<web_portal_ip>/` and `http://<web_portal_ip>:8080/`.
- Check `http://<web_portal_ip>/robots.txt` (disallows `/internal/`).
- Browse `http://<web_portal_ip>/internal/` (autoindex on).
- Open `patch-notes.txt` → **Part 1: m1dt3rm**

### Step 3b: SSH breadcrumb (file server: bonus path)

- SSH is running on non-standard port 2222 with weak credentials (`admin:admin`).
- Students who discover and log in will find `/home/admin/migration_email.txt`: an email fragment that explicitly mentions anonymous FTP access and debug info in the DC's SMB server string.
- This rewards students who enumerate the full port range and test weak creds, giving them a shortcut to the next steps.

### Step 4: Flag part 2 (file server)

- Anonymous FTP: `ftp <file_server_ip>`, login `anonymous`, password blank.
  - `get welcome-packet.txt`
- Or SMB guest: `smbclient //<file_server_ip>/public -N -c "get welcome-packet.txt"`
- Content → **Part 2: n3tw0rk**

### Step 5: Flag part 3 (domain controller)

- Enumerate SMB: `smbclient -L //<dc_ip> -N`
- The server string in the output contains **Flag Part 3 of 3: 3num**
- Alternative: `nmap --script smb-os-discovery <dc_ip>` or `enum4linux -a <dc_ip>`

### Step 6: Assemble the flag

Combine in order: **OCR{m1dt3rm_n3tw0rk_3num}**

Students submit this full string to complete the lab.

## Target Summary

| Machine       | Ports              | Flag part | Where to find it                    |
|---------------|--------------------|-----------|-------------------------------------|
| Web portal    | 80, 8080           | m1dt3rm   | `/internal/patch-notes.txt`         |
| File server   | 21, 445, 2222      | n3tw0rk   | FTP/SMB `welcome-packet.txt`       |
| Domain controller | 88, 139, 389, 445, 3389 | 3num | SMB server string                   |

**Bonus path**: SSH on port 2222 (file server) with `admin:admin` credentials contains `migration_email.txt`: an email fragment pointing to anonymous FTP and the DC's SMB server string debug info.

## Hints & Scoring

This is a midterm assessment. Hints are limited and carry a point penalty:

- **2 hints available** (no time lock; available immediately)
- **Each hint costs 5 points** deducted from the student's score
- Hints provide directional guidance only; they do not reveal specific flag parts, exact commands, or the solution

| Hints used | Scoring impact |
|------------|---------------|
| 0          | +25 bonus (no hints used) |
| 1          | -5 deduction |
| 2          | -10 deduction |

## Randomization

The lab has `randomize_ip_offsets: true` in `lab.yaml`. The platform assigns each student three random last octets (2-254) for the three services, so students cannot guess IPs and must perform a real subnet scan.

## Platform Configuration

- **Visibility**: `course`: this lab does NOT appear on the Exercises page; it is only accessible when assigned to a course
- **Track/Level**: None (`level_id = NULL`); appears under "Course Assessments" in the instructor panel
- **Display name**: Instructors can customize the title per course using the pencil icon in the Exercises sub-tab (e.g., "Midterm Exam - Network Enumeration")
- **Start date**: Use the assignment start_date to hide lab content from students until the exam begins

### Recommended Deployment Steps

1. Run lab discovery to import the lab (it will be created with `visibility: course`)
2. Open a course in the Instructor Panel
3. Assign the lab from the "Course Assessments" group
4. (Optional) Rename it using the pencil icon
5. Create an assignment with a future start date
6. Add the lab to the assignment
7. Students see the assignment title but cannot access the lab until the start date

## Validation

Run from the project root:

```bash
python3 scripts/validate-lab.py labs/Windows/windows-10-1-network-enumeration-assessment/
```

The full flag **OCR{m1dt3rm_n3tw0rk_3num}** must appear in this README for the flag-consistency check to pass.
