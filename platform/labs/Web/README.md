# Web Application Security Exercises

## Overview

The directory contains comprehensive Web Application Security exercises with hands-on labs designed using a **baby-steps approach** with extensive repetition. Each lab builds incrementally on previous skills, ensuring students master each web vulnerability type through practice before moving to more complex scenarios.

## Exercise Scaffolding

### Learning Philosophy

1. **Repetition**: Each vulnerability type is practiced multiple times before moving on
2. **Incremental Complexity**: Each lab adds ONE new concept to previously mastered skills
3. **Pattern Recognition**: Students learn patterns (reconnaissance → identification → exploitation) that repeat across vulnerability types
4. **Real-World Application**: Labs use realistic vulnerable applications, not toy examples
5. **HTB-Style Hostnames**: Labs use .lab hostnames requiring /etc/hosts modification

## Lab Organization Structure

```
labs/Web/
├── web-1-1-basic-directory-enumeration/
│   ├── lab.yaml              # Lab metadata with hostnames
│   ├── docker-compose.yml    # Container definitions with varied IP offsets
│   ├── README.md             # Instructor notes
│   └── containers/
│       └── webserver/
│           └── Dockerfile    # Container configuration
├── web-1-2-technology-identification/
│   └── ...
└── ... (40-50 total labs)
```

## Exercise Progression

### Level 1: Web Reconnaissance (6 labs)
**Difficulty**: Beginner  
**Focus**: Building enumeration and information gathering skills

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 1.1 | Basic Directory Enumeration | gobuster, dirb, directory discovery |
| 1.2 | Technology Identification | Wappalyzer, manual identification, headers |
| 1.3 | HTTP Methods Enumeration | OPTIONS, PUT, DELETE, method testing |
| 1.4 | Header Analysis | Security headers, information disclosure |
| 1.5 | Subdomain Discovery | DNS enumeration, subdomain brute forcing |
| 1.6 | Comprehensive Web Reconnaissance | Complete reconnaissance workflow |

**Repetition**: Students practice web enumeration 6 times, building from basic to comprehensive.

**Hostnames**: `recon.lab`, `target.lab`, `app.lab`

---

### Level 2: Injection Vulnerabilities (10 labs)
**Difficulty**: Beginner to Intermediate  
**Focus**: SQL injection, command injection, and related vulnerabilities

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 2.1 | Basic SQL Injection (GET) | SQL injection in GET parameters |
| 2.2 | SQL Injection (POST) | SQL injection in POST parameters |
| 2.3 | SQL Injection (UNION) | UNION-based SQL injection |
| 2.4 | SQL Injection (Blind) | Blind SQL injection, boolean-based |
| 2.5 | SQL Injection (Time-Based) | Time-based blind SQL injection |
| 2.6 | Command Injection | OS command injection vulnerabilities |
| 2.7 | LDAP Injection | LDAP query injection |
| 2.8 | NoSQL Injection | MongoDB, NoSQL injection |
| 2.9 | SQL Injection Authentication Bypass | Authentication bypass via SQL injection |
| 2.10 | Comprehensive Injection Testing | Multiple injection types in one app |

**Repetition**: Students practice injection attacks 10 times with increasing complexity.

**Hostnames**: `shop.lab`, `api.lab`, `admin.lab`, `db.lab` (internal)

**Multi-Container**: Web server + database containers with varied IP offsets

---

### Level 3: Authentication Attacks (8 labs)
**Difficulty**: Intermediate  
**Focus**: Authentication bypass, session management, brute forcing

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 3.1 | Brute Force Login | Hydra, Burp Suite Intruder |
| 3.2 | Session Hijacking | Cookie theft, session fixation |
| 3.3 | Session Fixation | Session ID manipulation |
| 3.4 | Password Reset Flaw | Password reset token vulnerabilities |
| 3.5 | Weak Password Policy | Weak password requirements |
| 3.6 | MFA Bypass | Multi-factor authentication bypass |
| 3.7 | Account Enumeration | Username enumeration techniques |
| 3.8 | Comprehensive Auth Testing | Complete authentication testing |

**Repetition**: Students practice authentication attacks 8 times.

**Hostnames**: `login.lab`, `secure.lab`, `auth.lab`

---

### Level 4: Cross-Site Scripting (XSS) (8 labs)
**Difficulty**: Intermediate  
**Focus**: Reflected, stored, and DOM-based XSS

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 4.1 | Reflected XSS (Basic) | Basic reflected XSS in GET parameters |
| 4.2 | Reflected XSS (Advanced) | Filter bypass, encoding |
| 4.3 | Stored XSS (Basic) | Stored XSS in user input |
| 4.4 | Stored XSS (Advanced) | Complex stored XSS scenarios |
| 4.5 | DOM-Based XSS | Client-side XSS, DOM manipulation |
| 4.6 | XSS Filter Bypass | WAF bypass, encoding techniques |
| 4.7 | XSS to Cookie Theft | Session hijacking via XSS |
| 4.8 | Comprehensive XSS Testing | Multiple XSS types in one app |

**Repetition**: Students practice XSS attacks 8 times across different contexts.

**Hostnames**: `blog.lab`, `forum.lab`, `comment.lab`

---

### Level 5: File Vulnerabilities (8 labs)
**Difficulty**: Intermediate  
**Focus**: File upload, LFI, RFI, path traversal

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 5.1 | Unrestricted File Upload | Basic file upload vulnerability |
| 5.2 | File Upload Type Validation | MIME type, extension validation |
| 5.3 | File Upload Bypass | Bypassing upload restrictions |
| 5.4 | Local File Inclusion (LFI) | LFI vulnerabilities |
| 5.5 | Remote File Inclusion (RFI) | RFI vulnerabilities |
| 5.6 | Path Traversal | Directory traversal attacks |
| 5.7 | File Disclosure | Sensitive file disclosure |
| 5.8 | Comprehensive File Testing | Multiple file vulnerabilities |

**Repetition**: Students practice file-related attacks 8 times.

**Hostnames**: `files.lab`, `upload.lab`, `storage.lab`

---

### Level 6: Advanced Web Exploitation (8 labs)
**Difficulty**: Advanced  
**Focus**: SSRF, XXE, deserialization, advanced techniques

| Lab | Name | Skills Practiced |
|-----|------|------------------|
| 6.1 | Server-Side Request Forgery (SSRF) | SSRF to internal services |
| 6.2 | XML External Entity (XXE) | XXE injection attacks |
| 6.3 | Insecure Deserialization | Object deserialization vulnerabilities |
| 6.4 | Template Injection | Server-side template injection |
| 6.5 | Race Conditions | Time-of-check to time-of-use |
| 6.6 | HTTP Request Smuggling | Request smuggling attacks |
| 6.7 | Advanced SSRF | SSRF with protocol handlers |
| 6.8 | Comprehensive Advanced Exploitation | Multiple advanced techniques |

**Repetition**: Students practice advanced exploitation 8 times.

**Hostnames**: `internal.lab`, `api-internal.lab`, `admin-internal.lab`

**Multi-Container**: Web server + internal services with varied IP offsets

---

## Skill Repetition Matrix

| Skill | Number of Labs | Progression |
|-------|---------------|-------------|
| Web Reconnaissance | 6 labs | Directory enum → Tech ID → Methods → Headers → Subdomains → Comprehensive |
| SQL Injection | 10 labs | GET → POST → UNION → Blind → Time-based → Auth bypass → Comprehensive |
| Command Injection | 3 labs | Basic → Advanced → Comprehensive |
| Authentication | 8 labs | Brute force → Session hijack → Fixation → Reset → MFA → Enum → Comprehensive |
| XSS | 8 labs | Reflected basic → Advanced → Stored → DOM → Filter bypass → Cookie theft → Comprehensive |
| File Vulnerabilities | 8 labs | Upload basic → Validation → Bypass → LFI → RFI → Traversal → Disclosure → Comprehensive |
| Advanced | 8 labs | SSRF → XXE → Deserialization → Template → Race → Smuggling → Advanced SSRF → Comprehensive |

## Total Lab Count: 48 Labs

## Lab File Structure

Each lab follows this exact structure:

```
web-{level}-{number}-{lab-slug}/
├── lab.yaml              # Lab metadata with hostnames
├── docker-compose.yml    # Container definitions with varied IP offsets
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
category: web
duration_minutes: 60-180
objectives:
  - First objective
  - Second objective
  - Capture the flag

# Optional: Hostname mappings for .lab domains
hostnames:
  - ip_offset: "17"
    hostname: "vulnerable.lab"
    description: "Main web application"
  - ip_offset: "23"
    hostname: "api.vulnerable.lab"
    description: "Internal API endpoint"
```

### docker-compose.yml Structure

```yaml
version: '3.8'

services:
  webserver:
    build:
      context: ./containers/webserver
      dockerfile: Dockerfile
    hostname: webserver
    labels:
      ip_offset: "17"  # Varied offsets (17, 23, 47, etc.)
    restart: unless-stopped

  database:
    build:
      context: ./containers/database
      dockerfile: Dockerfile
    hostname: db-mysql
    labels:
      ip_offset: "31"  # Different offset for second service
    restart: unless-stopped
```

### Flag Format

All flags use the format: `OCR{descriptive_flag_name}`

Examples:
- `OCR{d1r3ct0ry_3num3r4t10n_b4s1c}`
- `OCR{sql_1nj3ct10n_g3t_b4s1c}`
- `OCR{xss_r3fl3ct3d_b4s1c}`

## Hostname Support (.lab Domains)

### HTB-Style Hostname Resolution

Labs use `.lab` hostnames that require `/etc/hosts` modification, similar to HackTheBox:

1. **Platform displays hostname mappings** in the active lab panel
2. **Students add entries to /etc/hosts**:
   ```
   <target_ip>    vulnerable.lab
   <target_ip>    api.vulnerable.lab
   ```
   > **Note:** The platform's active lab panel shows the exact IPs for each hostname. Use those values when editing `/etc/hosts`.
3. **Access applications via hostname**: `http://vulnerable.lab`

### Benefits

- **Realistic**: Simulates real-world scenarios with domain names
- **Educational**: Teaches DNS/hostname concepts
- **Professional**: Matches industry-standard platforms (HTB, TryHackMe)

## Varied IP Offsets

### Realistic Network Simulation

Each student gets a dedicated subnet `10.100.{user_id}.0/24`. Within that subnet, each lab's containers use varied IP offsets, so the full address is `10.100.{user_id}.{offset}`.

Students must discover target IPs through network scanning (nmap) rather than guessing predictable addresses.

**Benefits:**
- Simple, predictable subnet per student (`10.100.{user_id}.0/24`)
- IP offsets vary across labs, requiring network reconnaissance
- More realistic network simulation
- Better prepares students for real assessments where IPs are unknown

**Range**: Offsets 10-250 per subnet

## Tools Students Will Use

### Reconnaissance
- **gobuster**: Directory enumeration
- **dirb**: Alternative directory enumeration
- **ffuf**: Fast web fuzzer
- **Wappalyzer**: Technology identification
- **Burp Suite**: Web application security testing

### Injection
- **sqlmap**: Automated SQL injection tool
- **Burp Suite**: Manual injection testing
- **curl**: Command-line HTTP client

### Authentication
- **Hydra**: Brute force tool
- **Burp Suite Intruder**: Custom brute forcing
- **John the Ripper**: Password cracking

### XSS
- **Browser DevTools**: Testing XSS payloads
- **Burp Suite**: XSS testing and exploitation
- **Custom payloads**: Various XSS vectors

### File Vulnerabilities
- **Burp Suite**: File upload testing
- **curl**: File retrieval
- **Custom scripts**: LFI/RFI exploitation

### Advanced
- **Burp Suite**: SSRF, XXE testing
- **Custom payloads**: Deserialization, template injection
- **Protocol handlers**: SSRF with various protocols

## Prerequisites

Students should have:
- Basic Linux command line knowledge
- Understanding of web technologies (HTML, HTTP, databases)
- Access to Kali Linux VM with tools installed
- Basic penetration testing concepts
- Understanding of web application architecture

## Usage

### For Instructors

1. Review lab README.md for solution walkthrough
2. Test lab deployment: `cd web-{lab-slug} && docker compose build`
3. Provide students with target hostnames and lab objectives
4. Monitor student progress through platform interface

### For Students

1. Receive target hostnames from platform interface
2. Add hostnames to `/etc/hosts` file
3. Read lab objectives in platform interface
4. Follow reconnaissance → identification → exploitation pattern
5. Capture flag using `OCR{}` format
6. Submit flag through platform

## Assessment Criteria

Each lab includes:
- Clear learning objectives
- Step-by-step solution walkthrough (in README.md)
- Common mistakes documentation
- Progressive hints for struggling students
- Realistic flag placement requiring exploitation
- Hostname mappings for .lab domains

## Lab Naming Convention

Labs follow this naming pattern:
```
web-{level}-{number}-{descriptive-slug}
```

Examples:
- `web-1-1-basic-directory-enumeration`
- `web-2-1-basic-sql-injection-get`
- `web-4-3-stored-xss-basic`
- `web-6-1-server-side-request-forgery`

## Platform Integration

The lab platform automatically:
- Discovers labs by scanning for `lab.yaml` files
- Reads metadata including hostnames to populate lab catalog
- Uses `docker-compose.yml` when students launch labs
- Applies network configuration based on `ip_offset` labels
- Creates isolated networks: `10.100.{user_id}.{ip_offset}`
- Displays hostname mappings in active lab panel
- Provides copyable `/etc/hosts` entries

## OWASP Top 10 Coverage

The exercises cover all OWASP Top 10 (2021) categories:

1. **A01: Broken Access Control** - Authentication labs (Level 3)
2. **A02: Cryptographic Failures** - Covered in authentication labs
3. **A03: Injection** - Level 2 (SQL, Command, LDAP, NoSQL)
4. **A04: Insecure Design** - Covered across all labs
5. **A05: Security Misconfiguration** - Header analysis, technology identification
6. **A06: Vulnerable Components** - Technology identification labs
7. **A07: Authentication Failures** - Level 3 (authentication attacks)
8. **A08: Software and Data Integrity** - Deserialization labs
9. **A09: Security Logging Failures** - Covered in comprehensive labs
10. **A10: SSRF** - Level 6 (SSRF labs)

## Learning Progression Summary

1. **Reconnaissance Mastery** (Labs 1.1-1.6): Students practice web enumeration 6 times
2. **Injection Mastery** (Labs 2.1-2.10): Students practice injection attacks 10 times
3. **Authentication Mastery** (Labs 3.1-3.8): Students practice authentication attacks 8 times
4. **XSS Mastery** (Labs 4.1-4.8): Students practice XSS attacks 8 times
5. **File Vulnerability Mastery** (Labs 5.1-5.8): Students practice file attacks 8 times
6. **Advanced Exploitation** (Labs 6.1-6.8): Students practice advanced techniques 8 times

## Support

For questions or issues:
- Review individual lab README.md files for specific solutions
- Check LAB_DEPLOYMENT.md in repository root for deployment issues
- Contact platform administrator for technical issues

