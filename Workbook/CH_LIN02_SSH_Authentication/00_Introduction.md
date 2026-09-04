# Chapter L2: SSH Authentication & Discovery

## Why SSH Authentication Matters

In Chapter L1, you scanned networks and identified open ports. You discovered that services like Secure Shell (SSH) were listening, and you gathered version banners that hinted at what lay behind those ports. But scanning only tells you what doors exist; it does not open them.

SSH authentication is the first real step from reconnaissance into exploitation. When a penetration tester obtains valid credentials; whether through password spraying, credential dumps, or social engineering; an SSH login provides direct access to the target system. From that shell session, every file, every user account, and every misconfiguration becomes reachable.

In real-world engagements, compromised SSH credentials remain one of the most common initial access vectors. Weak passwords, reused credentials, and default accounts give attackers a foothold that no firewall can prevent. Once inside, the attacker operates as a legitimate user, blending in with normal traffic and bypassing network-level defenses entirely.

## What You Will Learn

The three labs in this chapter guide you through the SSH authentication and discovery process:

- **Authenticate** to an SSH server using provided credentials and extract information from the login banner
- **Enumerate** the logged-in user's identity, group memberships, and privilege level to map escalation paths
- **Explore** the file system beyond the home directory to locate sensitive configuration files, credentials, and backups

By the end of the chapter, you will understand how a single set of compromised credentials can cascade into full system access, database compromise, and lateral movement across a network.

## What Is SSH Authentication?

SSH provides encrypted remote access to a system. Two primary authentication methods exist:

- **Password authentication**: the client sends a username and password over the encrypted channel. The server verifies them against its local database or a directory service.
- **Key-based authentication**: the client proves ownership of a private key that matches a public key stored on the server. No password crosses the network.

Once authenticated, the server spawns a shell session for the user. Every command you type travels through the encrypted tunnel, and every response returns the same way. The session persists until you type `exit` or the connection drops.

From a defender's perspective, SSH is both essential and dangerous. Administrators rely on it for remote management, but every SSH account is a potential entry point for an attacker who obtains valid credentials.

## How SSH Differs from Scanning

Scanning with Nmap told you that port 22 was open and running OpenSSH. That was the map. Authentication is walking through the door.

Once inside, you operate as a real user on the system. You can read files the user owns, run commands the user is permitted to execute, and discover information that no external scan could ever reveal; database passwords in configuration files, private SSH keys for lateral movement, and sudo rules that grant root access.

The transition from scanning to authentication marks the boundary between passive reconnaissance and active exploitation. Everything you do after login leaves traces in system logs, so understanding what information to gather; and gathering it efficiently; is a core penetration testing skill.

## The SSH Attack Workflow

The three labs follow a natural progression from login to deep file system exploration:

```mermaid
graph LR
    A[Exercise L2.1] --> B[Exercise L2.2]
    B --> C[Exercise L2.3]

    A; "SSH Login &\nMOTD Analysis" --> B
    B; "User Enumeration &\nPrivilege Check" --> C
    C; "File System\nExploration" --> D[Ch L3]
```

Each lab expands the scope of your discovery. Exercise L2.1 focuses on the login process itself and the information the server volunteers. Exercise L2.2 digs into user identity and privilege levels. Exercise L2.3 pushes beyond the home directory into web application files where the highest-value secrets reside.

## Before You Start

Before beginning the labs in this chapter, confirm the following:

- [ ] Completed all three labs in Chapter L1 (Network Scanning)
- [ ] Connected to the lab environment VPN
- [ ] Terminal open with SSH client available (verify with `ssh -V`)
- [ ] Notebook ready to record credentials, flags, and findings
- [ ] Familiar with basic Linux commands: `ls`, `cat`, `cd`, `pwd`
- [ ] Reviewed any credentials or host information gathered in Chapter L1

Once every item is checked, proceed to Exercise L2.1.
