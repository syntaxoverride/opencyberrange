# Chapter 9: Review

## What You Learned

Over three labs, you progressed from anonymous network enumeration to a complete penetration test methodology. Exercise 9.1 demonstrated that guest access and HTTP misconfigurations allow data extraction without any credentials. Exercise 9.2 showed how a single set of credentials can compromise multiple services through credential reuse testing with CrackMapExec. Exercise 9.3 combined null session enumeration, credential attacks, and structured documentation into a full penetration test that mirrors professional engagements.

The chapter brought together every technique from the Windows track; port scanning, service enumeration, SMB reconnaissance, credential testing, and multi-protocol exploitation; into a repeatable assessment methodology. The progression from unauthenticated access to authenticated exploitation to complete penetration testing reflects how real-world assessments escalate from initial reconnaissance to full compromise.

## The Progression You Followed

Each lab added complexity and new techniques while building on the skills from the previous exercise:

```mermaid
graph LR
    A["9.1 Windows Network<br/>Assessment"] --> B["9.2 Multi-Service<br/>Exploitation"]
    B --> C["9.3 Complete<br/>Penetration Test"]

    style A fill:#4a90d9,color:#fff
    style B fill:#e8a735,color:#fff
    style C fill:#6aaa64,color:#fff
```

| Exercise | What You Practiced | Key Skill Added |
|-----|-------------------|-----------------|
| 9.1 | Guest SMB access, HTTP flag retrieval | Unauthenticated assessment; no credentials needed |
| 9.2 | Credential testing across SMB, SSH, RDP | Multi-protocol exploitation with CrackMapExec |
| 9.3 | Null sessions, credential reuse, full methodology | Complete penetration test from recon to reporting |

---

## Self-Assessment

Answer the following questions without looking back at the walkthroughs. If you get stuck on a question, revisit that lab before moving on.

**1.** What Nmap flags would you use to perform a full service scan with default scripts?

> &nbsp;
>
> &nbsp;

**2.** How do you list SMB shares using a null session with smbclient?

> &nbsp;
>
> &nbsp;

**3.** What CrackMapExec command tests the credentials `admin:password123` against SSH on a target?

> &nbsp;
>
> &nbsp;

**4.** What does the `(Pwn3d!)` indicator mean in CrackMapExec output?

> &nbsp;
>
> &nbsp;

**5.** What does the SMB configuration `map to guest = Bad User` do, and why is it a security risk?

> &nbsp;
>
> &nbsp;

**6.** Name the six phases of a penetration testing methodology in order.

> &nbsp;
>
> &nbsp;

---

## Command Cheat Sheet

Keep the following reference handy for assessments and future labs.

| Command | What It Does |
|---------|-------------|
| `nmap -sV -sC <target>` | Full port scan with version detection and default scripts |
| `smbclient -L //<target> -N` | List SMB shares using a null session |
| `smbclient //<target>/<share> -N` | Connect to a share using a null session |
| `smbclient -L //<target> -U user%pass` | List shares with authenticated credentials |
| `smbmap -H <target>` | Map share permissions (anonymous) |
| `smbmap -H <target> -u user -p pass` | Map share permissions (authenticated) |
| `enum4linux -a <target>` | Full SMB/RPC enumeration (users, shares, groups, policies) |
| `crackmapexec smb <target> -u user -p pass` | Test credentials against SMB |
| `crackmapexec ssh <target> -u user -p pass` | Test credentials against SSH |
| `crackmapexec rdp <target> -u user -p pass` | Test credentials against RDP |
| `curl http://<target>/flag.txt` | Retrieve a file from an HTTP server |
| `ssh user@<target>` | Connect to target via SSH |

---

## Connect the Dots: What Comes Next

You have completed the Windows assessment track. Over nine chapters, you progressed from scanning a single port to executing a complete penetration test across multiple services. The skills you built; port scanning, service enumeration, SMB (Server Message Block) reconnaissance, credential attacks, LDAP (Lightweight Directory Access Protocol) enumeration, RDP (Remote Desktop Protocol) exploitation, WinRM (Windows Remote Management) access, credential reuse, and structured assessment methodology; form the foundation for every penetration test you will perform.

The Linux track applies similar methodology to Linux-specific services. SSH (Secure Shell) enumeration, authentication attacks, and post-exploitation techniques use many of the same tools you already know (Nmap, CrackMapExec, SSH) but target different service configurations and file system layouts. The Web track introduces HTTP-based vulnerabilities like directory traversal, command injection, and insecure API endpoints. The Network track covers traffic analysis using packet capture tools like tcpdump and Wireshark.

Each track builds on the same core methodology: scan, enumerate, identify vulnerabilities, exploit, and document. The tools and protocols change, but the approach stays the same.

---

## Self-Assessment Answer Key

**1.** `nmap -sV -sC <target>`: the `-sV` flag enables service version detection and `-sC` runs Nmap's default NSE scripts for additional enumeration.

**2.** `smbclient -L //<target> -N`: the `-L` flag lists shares and `-N` sends a null session (no password).

**3.** `crackmapexec ssh <target> -u admin -p password123`: the `ssh` keyword tells CME to test against the SSH service on port 22.

**4.** The `(Pwn3d!)` indicator means the authenticated account has local administrator privileges on the target. Administrative access allows command execution, credential dumping, and full system control.

**5.** The `map to guest = Bad User` setting maps authentication attempts with invalid usernames to the guest account instead of rejecting them. The server never returns an authentication failure for unknown users; it silently grants guest-level access. The setting is a security risk because it allows anyone to connect with any username and receive guest permissions, effectively disabling username validation.

**6.** The six phases are: (1) Reconnaissance, (2) Enumeration, (3) Vulnerability Identification, (4) Exploitation, (5) Post-Exploitation, (6) Reporting. Each phase produces outputs that feed into the next, and skipping phases leads to incomplete findings.
