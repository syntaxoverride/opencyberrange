# Windows Penetration Testing Exercises

## Overview

The directory contains comprehensive Windows penetration testing exercises with 47 hands-on labs designed using a **baby-steps approach** with extensive repetition. Each lab builds incrementally on previous skills, ensuring students master each technique through practice before moving to more complex scenarios.

## Exercise Scaffolding

### Learning Philosophy

1. **Repetition**: Each skill is practiced 3-5 times before moving on
2. **Incremental Complexity**: Each lab adds ONE new concept to previously mastered skills
3. **Pattern Recognition**: Students learn patterns (enumeration → authentication → exploitation) that repeat across services
4. **Confidence Building**: By the final test, students have seen every technique multiple times

## Lab Organization Structure

```
labs/Windows/
├── windows-1-1-basic-port-scan/
│   ├── lab.yaml              # Lab metadata
│   ├── docker-compose.yml    # Container definitions
│   ├── README.md             # Instructor notes
│   └── containers/
│       └── target/
│           └── Dockerfile    # Container configuration
├── windows-1-2-multiple-port-discovery/
│   └── ...
└── ... (47 total labs)
```

## Exercise Progression

### Module 1: Windows Reconnaissance Fundamentals (5 labs)
**Difficulty**: Beginner  
**Focus**: Building enumeration skills through repetition

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 1.1 | Basic Windows Port Scan | Basic nmap, SMB identification |
| 1.2 | Multiple Port Discovery | Full port scan, service identification |
| 1.3 | Windows Service Version Detection | nmap -sV, version interpretation |
| 1.4 | Windows OS Detection | nmap -O, OS fingerprinting |
| 1.5 | Comprehensive Windows Enumeration | Complete enumeration workflow |

**Repetition**: Students scan and enumerate 5 times, building from basic to comprehensive.

---

### Module 2: SMB Enumeration and Exploitation Part 1 (8 labs)
**Difficulty**: Beginner  
**Focus**: Mastering SMB enumeration through repetition

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 2.1 | SMB Connection Test | smbclient basic connection |
| 2.2 | SMB Share Listing | Share enumeration |
| 2.3 | SMB Anonymous Share Access | Anonymous access, file listing |
| 2.4 | SMB File Retrieval | File download from shares |
| 2.5 | SMB Null Session Connection | Null session syntax |
| 2.6 | SMB Null Session Share Enumeration | Null session enumeration |
| 2.7 | SMB User Enumeration via Null Session | User enumeration (rpcclient, enum4linux) |
| 2.8 | SMB Comprehensive Null Session Enumeration | Complete null session enumeration |

**Repetition**: Students work with SMB 8 times, from basic connection to comprehensive enumeration.

---

### Module 3: SMB Credential Attacks Part 2 (5 labs)
**Difficulty**: Beginner to Intermediate  
**Focus**: Building credential attack skills through repetition

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 3.1 | SMB Manual Credential Test | Manual authentication |
| 3.2 | SMB Multiple Credential Testing | Manual password testing |
| 3.3 | SMB Single User Brute Force | Hydra/Medusa brute forcing |
| 3.4 | SMB Username Enumeration and Brute Force | Enum + brute force combination |
| 3.5 | SMB Full Credential Attack | Complete attack chain |

**Repetition**: Students practice credential attacks 5 times, from manual to automated.

---

### Module 4: RDP Enumeration and Exploitation (6 labs)
**Difficulty**: Beginner  
**Focus**: Applying enumeration/authentication pattern to RDP

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 4.1 | RDP Service Detection | RDP port/service identification |
| 4.2 | RDP Version Enumeration | Version detection |
| 4.3 | RDP Manual Connection Test | xfreerdp basic connection |
| 4.4 | RDP Credential Guessing | Manual credential testing |
| 4.5 | RDP Brute Force Attack | RDP brute forcing |
| 4.6 | RDP Session Access and Flag Retrieval | Session management, post-exploitation |

**Repetition**: Students apply the enumeration → authentication → exploitation pattern to RDP.

---

### Module 5: WinRM Enumeration and Exploitation (6 labs)
**Difficulty**: Beginner to Intermediate  
**Focus**: Applying pattern to WinRM service

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 5.1 | WinRM Service Detection | WinRM port/service identification |
| 5.2 | WinRM Version and Configuration Enumeration | WinRM-specific enumeration |
| 5.3 | WinRM Manual Authentication | evil-winrm/winrm-cli connection |
| 5.4 | WinRM Credential Brute Force | WinRM brute forcing |
| 5.5 | WinRM Command Execution | Command execution via WinRM |
| 5.6 | WinRM File Retrieval | File operations via WinRM |

**Repetition**: Students apply the same pattern to WinRM, reinforcing learned techniques.

---

### Module 6: MS-SQL Enumeration and Exploitation (7 labs)
**Difficulty**: Intermediate  
**Focus**: Applying pattern to database service

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 6.1 | MS-SQL Service Detection | MS-SQL port/service identification |
| 6.2 | MS-SQL Version and Instance Enumeration | Database version enumeration |
| 6.3 | MS-SQL Manual Authentication | mssqlclient.py/sqlcmd connection |
| 6.4 | MS-SQL Credential Brute Force | MS-SQL brute forcing |
| 6.5 | MS-SQL Basic Query Execution | SQL query execution |
| 6.6 | MS-SQL xp_cmdshell Activation | xp_cmdshell configuration |
| 6.7 | MS-SQL File System Access via xp_cmdshell | File system access via SQL |

**Repetition**: Students apply the pattern to databases, adding SQL-specific techniques.

---

### Module 7: LDAP Enumeration and Exploitation (6 labs)
**Difficulty**: Intermediate  
**Focus**: Applying pattern to directory service

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 7.1 | LDAP Service Detection | LDAP port/service identification |
| 7.2 | LDAP Anonymous Bind Test | Anonymous LDAP bind |
| 7.3 | LDAP Base DN Enumeration | Base DN discovery |
| 7.4 | LDAP User Enumeration | User enumeration via LDAP |
| 7.5 | LDAP Group Enumeration | Group enumeration |
| 7.6 | LDAP Comprehensive Enumeration | Complete LDAP enumeration |

**Repetition**: Students apply the pattern to directory services, learning LDAP-specific queries.

---

### Module 8: Credential Reuse and Lateral Movement (5 labs)
**Difficulty**: Intermediate  
**Focus**: Combining previously learned skills, introducing automation with CrackMapExec

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 8.1 | Single Service Credential Discovery | Credential reuse within same service |
| 8.2 | Cross-Service Credential Reuse | Credential reuse across services |
| 8.3 | Multi-Service Credential Reuse | Credential reuse on multiple services |
| 8.4 | Credential Discovery and Reuse Chain | Complete chain (enum → discovery → reuse) |
| 8.5 | CME Credential Reuse Automation | CrackMapExec introduction, automation vs manual tools |

**Repetition**: Students practice credential reuse 4 times manually, then learn CME automation in lab 8.5.

**CME Introduction**: Lab 15.5 introduces CrackMapExec (CME), teaching students to automate credential testing across multiple protocols and targets. The lab bridges manual tool knowledge with industry-standard automation.

---

### Module 9: Comprehensive Windows Penetration Test (3 labs)
**Difficulty**: Intermediate  
**Focus**: Final comprehensive test using all learned skills, with CrackMapExec as primary automation tool

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 9.1 | Windows Network Assessment | Network-wide enumeration |
| 9.2 | Multi-Service Exploitation | Service-specific exploitation across network using CME |
| 9.3 | Complete Windows Penetration Test | Full penetration test with CME throughout attack chain |

**Repetition**: Students apply all skills in realistic scenarios, using CME for efficiency and automation.

**CME Application**: Labs 9.2 and 9.3 emphasize CME usage for network-wide testing, credential reuse, and post-exploitation, preparing students for real-world penetration testing scenarios.

---

## Skill Repetition Matrix

| Skill | Number of Labs | Progression |
|-------|---------------|-------------|
| Port Scanning | 5 labs | Basic → Multiple → Version → OS → Comprehensive |
| SMB Enumeration | 8 labs | Connect → List → Access → Null → Enum → Complete |
| SMB Credentials | 5 labs | Manual → Multiple → Brute → Enum+Brute → Full Chain |
| RDP Attacks | 6 labs | Detect → Version → Connect → Guess → Brute → Access |
| WinRM Attacks | 6 labs | Detect → Enum → Auth → Brute → Execute → File Access |
| MS-SQL Attacks | 7 labs | Detect → Version → Auth → Brute → Query → xp_cmdshell → File |
| LDAP Enumeration | 6 labs | Detect → Bind → Base DN → Users → Groups → Complete |
| Credential Reuse | 5 labs | Same Service → Cross Service → Multi Service → Full Chain → CME Automation |
| CME/Automation | 3 labs | CME Introduction → Multi-Service Exploitation → Complete Penetration Test |
| Comprehensive | 3 labs | Network Enum → Multi Exploit → Full Penetration Test |

## Total Lab Count: 48 Labs

## Lab File Structure

Each lab follows this exact structure:

```
windows-{level}-{number}-{lab-slug}/
├── lab.yaml              # Lab metadata with objectives
├── docker-compose.yml    # Container definitions with ip_offset labels
├── README.md             # Instructor notes with solution walkthrough
└── containers/
    └── {service-name}/
        └── Dockerfile    # Container configuration with OCR{} flags
```

### lab.yaml Structure

```yaml
name: Lab Name
description: Lab description
difficulty: beginner|intermediate|advanced
category: enumeration|web|network|privesc|forensics|crypto
duration_minutes: 60
objectives:
  - First objective
  - Second objective
  - Capture the flag
```

### docker-compose.yml Structure

```yaml
version: '3.8'

services:
  target:
    build:
      context: ./containers/target
      dockerfile: Dockerfile
    hostname: windows-target
    labels:
      ip_offset: "10"  # Required: 10-250, increments of 10
    restart: unless-stopped
```

### Flag Format

All flags use the format: `OCR{descriptive_flag_name}`

Examples:
- `OCR{b4s1c_p0rt_sc4n}`
- `OCR{smb_c0nn3ct}`
- `OCR{rdp_brut3_f0rc3}`

## Learning Progression Summary

1. **Enumeration Mastery** (Labs 1.1-1.5): Students scan and enumerate 5 times
2. **SMB Mastery** (Labs 2.1-3.5): Students work with SMB 13 times across enumeration and credential attacks
3. **Service Pattern Application** (Labs 4-7): Students apply enumeration → authentication → exploitation pattern 4 times (RDP, WinRM, MS-SQL, LDAP)
4. **Lateral Movement** (Labs 8.1-8.4): Students practice credential reuse 4 times with increasing complexity
5. **Automation Introduction** (Lab 8.5): Students learn CrackMapExec (CME) for credential reuse automation
6. **Comprehensive Testing** (Labs 9.1-9.3): Students apply all skills including CME in realistic scenarios

## Tools Students Will Use

### Manual Tools (Labs 1-8.4)
- **nmap**: Port scanning, service detection, version detection, OS detection
- **smbclient**: SMB share access and enumeration
- **enum4linux**: SMB enumeration automation
- **rpcclient**: RPC enumeration
- **Hydra/Medusa**: Credential brute forcing
- **xfreerdp**: RDP client
- **evil-winrm**: WinRM client (or SSH as alternative)
- **ldapsearch**: LDAP enumeration
- **mssqlclient.py**: MS-SQL client (or mysql as alternative)

### Automation Tools (Labs 8.5-9.3)
- **CrackMapExec (CME)**: Post-exploitation tool for Windows network assessment
  - Multi-protocol credential testing (SMB, RDP, WinRM, MSSQL, SSH, LDAP)
  - Network-wide enumeration and exploitation
  - Credential database management
  - Post-exploitation automation
  - See `CME_REFERENCE.md` for detailed documentation

## Prerequisites

Students should have:
- Basic Linux command line knowledge
- Understanding of networking fundamentals
- Access to Kali Linux VM with tools installed
- Basic penetration testing concepts (from previous modules if following full exercises)

## Usage

### For Instructors

1. Review lab README.md for solution walkthrough
2. Test lab deployment: `cd windows-{lab-slug} && docker-compose build`
3. Provide students with target IP and lab objectives
4. Monitor student progress through platform interface

### For Students

1. Receive target IP from instructor
2. Read lab objectives in platform interface
3. Follow enumeration → authentication → exploitation pattern
4. Capture flag using `OCR{}` format
5. Submit flag through platform

## Assessment Criteria

Each lab includes:
- Clear learning objectives
- Step-by-step solution walkthrough (in README.md)
- Common mistakes documentation
- Progressive hints for struggling students
- Realistic flag placement requiring exploitation

## Lab Naming Convention

Labs follow this naming pattern:
```
windows-{level}-{number}-{descriptive-slug}
```

Examples:
- `windows-1-1-basic-port-scan`
- `windows-2-5-smb-null-session-connection`
- `windows-3-3-smb-single-user-brute-force`
- `windows-9-3-complete-windows-penetration-test`

## Platform Integration

The lab platform automatically:
- Discovers labs by scanning for `lab.yaml` files
- Reads metadata to populate lab catalog
- Uses `docker-compose.yml` when students launch labs
- Applies network configuration based on `ip_offset` labels
- Creates isolated networks: `10.10.{user_id}.{ip_offset}`

## CrackMapExec (CME) Resources

- **CME_REFERENCE.md**: Comprehensive educational reference for CrackMapExec
  - What CME is and why it's used
  - CME vs manual tools comparison
  - Common CME commands
  - Installation and version information
  - Real-world use cases

## Support

For questions or issues:
- Review individual lab README.md files for specific solutions
- Check `CME_REFERENCE.md` for CrackMapExec documentation
- Check LAB_DEPLOYMENT.md in repository root for deployment issues
- Contact platform administrator for technical issues

