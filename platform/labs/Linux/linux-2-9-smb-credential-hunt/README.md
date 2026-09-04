# SMB Credential Hunt

## Overview
Hargrove Medical Group runs a Samba file server with multiple shares. Students
must enumerate available shares using anonymous access, discover leaked
credentials in a misconfigured share, and use those credentials to access a
restricted clinical share containing the second flag token.

## Difficulty
Intermediate

## Duration
40 minutes

## Objectives
1. Enumerate SMB shares on the target using anonymous/null session access.
2. Access the **public** share and locate the first assessment token embedded
   in an IT notes file.
3. Access the **records** share and extract service account credentials from a
   backup configuration file.
4. Authenticate to the **clinical** share with the discovered credentials and
   retrieve the second assessment token.
5. Assemble the complete flag from both tokens.

## Target Environment
| Host | Role | Services |
|------|------|----------|
| target (offset 27) | Samba file server | SMB (445/139) |

### Share Layout
- **public**: Guest-accessible. Contains a corporate welcome message, IT
  audit notes with Token 1, and a staff directory referencing the clinical
  share and the medsvc user.
- **records**: Guest-accessible. Contains a backup configuration file that
  leaks the medsvc account password.
- **clinical**: Restricted. Requires medsvc credentials. Contains the
  assessment marker with Token 2.

## Tools
- `smbclient`: Connect to and interact with SMB shares
- `enum4linux`: Automated SMB enumeration
- `nmap`: Port and service discovery

## Hints
Hints unlock at 15, 25, and 35 minutes to support unguided reinforcement
learning without giving away the flag.
