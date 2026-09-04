# Linux 4.3: Three-Hop Pivot

## Meridian Trust Bank: Three-Hop Lateral Movement

**Difficulty:** Intermediate
**Category:** Post-Exploitation
**Duration:** 55 minutes
**Week:** 11

## Overview

Students begin with SSH credentials for a teller workstation at Meridian Trust Bank. Through systematic enumeration of configuration files, they discover credentials to pivot to an internal application server, then use API keys found there to authenticate to a core banking API. The exercise demonstrates a realistic three-hop lateral-movement chain.

## Architecture

| Host   | Role                | IP Offset | Access        |
|--------|---------------------|-----------|---------------|
| host-a | Teller Workstation  | 15        | SSH (port 22) |
| host-b | Application Server  | 32        | SSH (port 22) |
| host-c | Core Banking API    | 48        | HTTP (port 8080) |

## Attack Path

1. SSH into the teller workstation (host-a) with provided credentials
2. Find database credentials in the banking application `.env` file
3. Collect assessment token 1 from host-a
4. Pivot to the application server (host-b) using discovered credentials
5. Find an API key in the gateway configuration on host-b
6. Collect assessment token 2 from host-b
7. Use the API key to authenticate to the core API (host-c) and retrieve token 3
8. Assemble the flag from all three tokens

## Skills Practiced

- Lateral movement across segmented networks
- Configuration file enumeration
- Credential harvesting from application configs
- API authentication and interaction
- Multi-hop pivot chains
