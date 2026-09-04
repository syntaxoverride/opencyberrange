# Chapter 9: Network Assessment

## What Is Network Assessment?

A network assessment is a structured, methodical evaluation of a target environment designed to identify every exploitable weakness across all exposed services. Rather than testing one protocol at a time, a network assessment combines reconnaissance, enumeration, vulnerability identification, and exploitation into a single cohesive process. The methodology ensures that no service is overlooked and that findings from one phase inform the next.

In professional penetration testing, a network assessment is the culmination of all individual techniques. Port scanning feeds into service enumeration. Service enumeration reveals misconfigurations. Misconfigurations lead to exploitation. Each phase produces data that sharpens the next, creating a feedback loop that drives the tester deeper into the target environment. The structured approach also makes the final report more credible; every finding is backed by a documented chain of evidence.

## Why Attackers Care

Attackers who follow a structured methodology achieve more complete compromise than those who test services in isolation. A guest-accessible SMB (Server Message Block) share might seem like a minor finding on its own, but when the same assessment discovers HTTP (Hypertext Transfer Protocol) content confirming the misconfiguration, RDP (Remote Desktop Protocol) accepting weak credentials, and SSH (Secure Shell) granting command-line access with those same credentials, the individual findings combine into a critical security gap.

The real power of a structured assessment is credential reuse discovery. Credentials found during SMB enumeration can be tested against every other service on the target. An attacker who discovers `admin:password123` on one service will immediately spray those credentials across SMB, RDP, and SSH. When the same password works on all three, a single weak password becomes a complete compromise.

Automated tools like **CrackMapExec** (CME) make multi-protocol credential testing fast and systematic. Combined with enumeration tools like **enum4linux** and **smbmap**, a penetration tester can move from initial scan to full access in minutes. Understanding how to chain these tools together; and when to use each one; is the core skill that separates a checklist-follower from an effective penetration tester.

## What You Will Learn

The three labs in this chapter bring together every technique you have practiced in previous chapters. Each lab increases the complexity: from anonymous enumeration and HTTP flag retrieval, to multi-service credential exploitation, to a complete penetration test methodology that mirrors professional engagements.

By the end of this chapter, you will be able to:

- Conduct a full network scan and identify all exposed services on a target
- Enumerate SMB shares using anonymous and guest access without credentials
- Retrieve sensitive data from misconfigured HTTP services
- Test discovered credentials across SMB, RDP, and SSH using CrackMapExec
- Perform null session enumeration to extract user and share information
- Execute a complete penetration test from reconnaissance through exploitation and documentation
- Chain individual techniques into a repeatable assessment methodology

## The Tools You Will Use

Each lab builds on tools you have used in previous chapters and combines them into multi-tool workflows. The table below shows every tool used in this chapter and where it first appears.

| Tool | Purpose | First Used |
|------|---------|------------|
| `nmap` | Port scanning and service version detection | Exercise 9.1 |
| `smbclient` | SMB share listing and file access | Exercise 9.1 |
| `smbmap` | SMB share permission mapping | Exercise 9.1 |
| `enum4linux` | Full SMB and LDAP enumeration | Exercise 9.1 |
| `curl` | HTTP content retrieval | Exercise 9.1 |
| `crackmapexec` | Multi-protocol credential testing (SMB, RDP, SSH) | Exercise 9.2 |
| `ssh` | Remote shell access and command execution | Exercise 9.2 |

## Lab Progression

The three labs follow a deliberate progression from anonymous enumeration to authenticated exploitation to a complete penetration test. Each lab adds new services, new techniques, and greater complexity:

```mermaid
graph LR
    A["9.1 Windows Network<br/>Assessment"] --> B["9.2 Multi-Service<br/>Exploitation"]
    B --> C["9.3 Complete<br/>Penetration Test"]

    style A fill:#4a90d9,color:#fff
    style B fill:#e8a735,color:#fff
    style C fill:#6aaa64,color:#fff
```

| Exercise | Focus | What It Adds |
|-----|-------|-------------|
| 9.1 | Windows Network Assessment | Guest SMB access, HTTP flag retrieval; no credentials needed |
| 9.2 | Multi-Service Exploitation | Credential testing across SMB, RDP, and SSH with CrackMapExec |
| 9.3 | Complete Windows Penetration Test | Null session enumeration, credential reuse, full pentest methodology |

Notice how the authentication requirements escalate: Exercise 9.1 uses only anonymous and guest access, Exercise 9.2 introduces known credentials, and Exercise 9.3 combines unauthenticated enumeration with authenticated exploitation. Do not worry about memorizing every command variation right now. Each lab walkthrough explains the specific tools and syntax before you run them.

## Before You Start

Make sure the following are in place before beginning Exercise 9.1:

- [ ] You have completed Chapter 2 (SMB Reconnaissance) and Chapter 3 (SMB Credential Attacks)
- [ ] You are comfortable with `smbclient`, `smbmap`, and `enum4linux` from previous chapters
- [ ] You understand how CrackMapExec tests credentials across multiple protocols
- [ ] You know the basics of SSH and RDP connectivity
- [ ] Your VPN is connected and your terminal is open
- [ ] You have a Kali Linux terminal with nmap, smbclient, smbmap, enum4linux, crackmapexec, curl, and ssh available
- [ ] You have verified connectivity to the target by pinging it or running a quick Nmap scan

If SMB enumeration or credential testing concepts from Chapters 2, 3, or 8 feel unclear, review those chapters before proceeding. The labs in this chapter assume you can already enumerate shares, test credentials, and interpret tool output.
