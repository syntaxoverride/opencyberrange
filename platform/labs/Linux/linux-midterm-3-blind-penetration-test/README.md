# Apex Meridian Group: Blind Penetration Test

## Overview
Week 9 reinforcement lab. A black-box penetration test against Apex Meridian Group's two-server infrastructure with zero step-by-step guidance.

**Difficulty:** Advanced
**Category:** Assessment
**Duration:** 90 minutes
**Flag format:** `OCR{...}`

## Lab Architecture

| Host | Role | IP Offset | Services |
|------|------|-----------|----------|
| webserver | Apex corporate site with file download | 13 | Flask (HTTP/80) |
| backend | Internal application server | 38 | OpenSSH (22) |

## Attack Path

Students must independently discover and chain the following phases:

1. **Reconnaissance**: Enumerate both hosts to discover available services
2. **Web Exploitation**: Identify the `/download` endpoint and exploit a directory traversal vulnerability to read sensitive configuration files
3. **Credential Discovery**: Extract backend SSH credentials from the application environment file
4. **Lateral Movement**: Pivot to the backend server using the discovered credentials
5. **Privilege Escalation**: Identify a SUID misconfiguration and escalate to root
6. **Flag Assembly**: Combine all three assessment markers into the final flag

## Assessment Markers

Three tokens are distributed across the infrastructure. Students must retrieve all three and assemble the complete flag.

- **Token 1:** Located on the web server in a configuration file accessible via directory traversal
- **Token 2:** Located in the deploy user's home directory on the backend server
- **Token 3:** Located in /root on the backend server (requires privilege escalation)

## Hints

Hints are delayed at assessment-level intervals (30/45/60 minutes) to encourage independent problem-solving before assistance is provided.
