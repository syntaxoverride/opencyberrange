# Week 15: Black Box CTF

## Titan Global Industries: Black Box Assessment

**Difficulty:** Advanced
**Category:** Assessment
**Duration:** 120 minutes
**Flag format:** `OCR{...}`

## Overview

This is a black box capture-the-flag exercise. Students are given no scenario
brief, no credentials, and no documentation. Four servers are in scope, each
containing one flag fragment. Students must chain together SQL injection,
credential pivoting, privilege escalation, and traffic analysis to recover all
four fragments and assemble the complete flag.

## Skills Assessed

- SQL injection (UNION-based)
- Web source code analysis
- SSH credential discovery and pivoting
- SUID binary exploitation for privilege escalation
- Network traffic (PCAP) analysis
- Multi-host attack chaining

## Environment

| Host           | IP Offset | Services       |
|----------------|-----------|----------------|
| server-alpha   | 11        | HTTP (Flask)   |
| server-bravo   | 27        | HTTP, SSH      |
| server-charlie | 41        | SSH            |
| server-delta   | 55        | SSH            |

## Notes for Instructors

- Hints unlock at 30, 50, and 70 minutes (assessment-level delays)
- Students should start with network reconnaissance (nmap) to discover all hosts
- The clue chain flows: alpha -> bravo -> charlie -> delta
- Each server yields exactly one flag fragment
- The flag fragments must be assembled in order (alpha, bravo, charlie, delta)
