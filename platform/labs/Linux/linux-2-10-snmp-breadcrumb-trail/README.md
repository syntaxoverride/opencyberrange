# SNMP Breadcrumb Trail

## Overview
Ridgeline Power Systems operates an ICS gateway that exposes SNMP with multiple community strings. Students must chain SNMP enumeration to uncover hidden credentials and ultimately gain SSH access.

## Learning Objectives
- Enumerate SNMP services using default community strings
- Discover non-default community strings through careful analysis of SNMP data
- Chain multiple enumeration techniques to progressively gain access
- Use discovered credentials to authenticate via SSH

## Attack Path
1. Walk SNMP with the default `public` community string to enumerate system info
2. Identify a hidden community string embedded in the `sysDescr` field
3. Walk SNMP again with the discovered community string to reveal SSH credentials
4. Log in via SSH using the extracted credentials
5. Read the flag from the user's home directory

## Services
| Service | Port      | Purpose                        |
|---------|-----------|--------------------------------|
| SNMP    | 161/UDP   | Network management (two communities) |
| SSH     | 22/TCP    | Remote administration          |

## Difficulty
Intermediate; requires chaining multiple enumeration steps.

## Duration
45 minutes
