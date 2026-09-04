# Exercise 9.3: Complete Windows Penetration Test

## Before You Begin

Exercise 9.1 covered anonymous enumeration and Exercise 9.2 demonstrated authenticated credential reuse. Exercise 9.3 brings everything together into a complete penetration test; starting with zero knowledge, discovering information through null sessions, testing credentials across all services, and documenting the full attack chain. Make sure you are comfortable with `enum4linux`, `smbclient`, `smbmap`, CrackMapExec (CME), and SSH from previous labs. Your VPN must be connected and your Kali terminal ready.

## Scenario

You are performing the final exercise in the FinanceCorp engagement. James Mitchell, the engagement lead, wants a complete penetration test that demonstrates the full attack chain; from initial reconnaissance through exploitation and evidence collection. You are starting with no credentials and no prior knowledge of the target. Your job is to enumerate the target, discover access paths, exploit weaknesses, and retrieve the flag.

## Your Objectives

- Conduct a full port scan and service enumeration
- Perform null session enumeration to extract user and share information
- List shares anonymously to confirm unauthenticated access paths
- Test discovered or common credentials against all exposed services
- Enumerate authenticated SMB shares and identify sensitive data
- Connect via SSH and retrieve the flag
- Document every finding in a structured format

---

## Background: Penetration Testing Methodology

A penetration test follows six distinct phases, each producing outputs that feed into the next. Skipping phases or testing out of order leads to incomplete findings and unreliable conclusions. The methodology exists to ensure reproducibility; another tester following the same steps should arrive at the same results.

The six phases are:

1. **Reconnaissance**: Identify open ports, running services, and software versions
2. **Enumeration**: Extract detailed information from each service (users, shares, configurations)
3. **Vulnerability Identification**: Map findings against known weaknesses and misconfigurations
4. **Exploitation**: Confirm vulnerabilities by demonstrating access or data extraction
5. **Post-Exploitation**: Expand access, collect evidence, and determine full impact
6. **Reporting**: Document every finding with evidence, severity ratings, and remediation guidance

```mermaid
graph LR
    A["1. Recon"] --> B["2. Enumerate"]
    B --> C["3. Vuln ID"]
    C --> D["4. Exploit"]
    D --> E["5. Post-Exploit"]
    E --> F["6. Report"]

    style A fill:#4a90d9,color:#fff
    style B fill:#4a90d9,color:#fff
    style C fill:#e8a735,color:#fff
    style D fill:#d9534f,color:#fff
    style E fill:#d9534f,color:#fff
    style F fill:#6aaa64,color:#fff
```

Exercise 9.3 targets a Windows server configured with `map to guest = Bad User` in its SMB (Server Message Block) configuration. The `map to guest = Bad User` setting means that any authentication attempt with an invalid username is silently mapped to the guest account instead of being rejected. An attacker can exploit this behavior by connecting with any username and receiving guest-level access; the server never reports an authentication failure. Null session and anonymous connections succeed because the server treats unknown users as guests rather than blocking them.

## Tool Primer: enum4linux Comprehensive Enumeration

The `enum4linux` tool wraps several SMB and RPC (Remote Procedure Call) queries into a single command. Running it with the `-a` flag performs all available enumeration checks and produces a consolidated report covering users, shares, groups, password policies, and OS (Operating System) information.

!!! kali "Run full enumeration with enum4linux"
    Running `enum4linux` with the `-a` flag performs all available enumeration checks in one pass.

    ```bash
    enum4linux -a <target_ip>
    ```

    The output is a consolidated report covering users, shares, groups, password policies, and OS information.

| Flag | Purpose |
|------|---------|
| `-a` | Run all enumeration checks (users, shares, groups, policies, OS info) |
| `-U` | Enumerate users only |
| `-S` | Enumerate shares only |
| `-G` | Enumerate groups only |
| `-P` | Enumerate password policies only |

**Key output sections to review:**

| Section | What It Reveals |
|---------|----------------|
| OS Information | Windows version, domain/workgroup name |
| User Enumeration | Local and domain user accounts |
| Share Enumeration | All SMB shares and their types |
| Group Enumeration | Local and domain groups with memberships |
| Password Policy | Lockout thresholds, password complexity requirements |

The output from `enum4linux -a` is lengthy. Focus on user accounts (potential targets for credential attacks), share names (potential data access paths), and password policy (determines whether brute force is viable without triggering lockouts).

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** then **Windows** then **Level 2**
- Click **Launch** on "Complete Windows Penetration Test"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Conduct Full Reconnaissance

!!! kali "Full reconnaissance scan"
    Begin with a full Nmap scan to identify every open port and service on the target. The `-sV` flag performs service version detection, and `-sC` runs default NSE (Nmap Scripting Engine) scripts for additional enumeration.

    ```bash
    nmap -sV -sC <target_ip>
    ```

    You should see three services: SMB on port 445, RDP on port 3389, and SSH on port 22. Record every port, service name, and version string. The default scripts may also reveal the target's hostname, domain membership, and SMB signing configuration.

### Step 3: Perform Null Session Enumeration

!!! kali "Null session enumeration"
    Run `enum4linux` with the `-a` flag to extract as much information as possible without credentials.

    ```bash
    enum4linux -a <target_ip>
    ```

    The tool attempts null session connections and queries the target for user accounts, share listings, group memberships, and password policies. Because the target is configured with `map to guest = Bad User`, these queries succeed even though you have not provided credentials. Review the output carefully and record any usernames, share names, and policy details.

### Step 4: List Shares Anonymously

!!! kali "List shares anonymously"
    Confirm the share listings from `enum4linux` by using `smbclient` with a null session. The `-N` flag suppresses the password prompt, sending a null session request.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    Compare the share list against the `enum4linux` output to verify consistency. Look for non-default shares like `private`, `public`, or `data`: these are administrator-created shares that may contain sensitive files.

### Step 5: Test Credentials on All Services

Test common credentials against every exposed service using CrackMapExec, one protocol at a time.

!!! kali "Test credentials on SMB"
    Start the sweep with the SMB protocol keyword.

    ```bash
    crackmapexec smb <target_ip> -u admin -p password123
    ```

    A `[+]` result, and especially the `(Pwn3d!)` marker, confirms administrative SMB access.

!!! kali "Test credentials on SSH"
    Repeat the test with the SSH protocol keyword.

    ```bash
    crackmapexec ssh <target_ip> -u admin -p password123
    ```

    A `[+]` result confirms the same credentials open a shell service.

!!! kali "Test credentials on RDP"
    Finish the sweep with the RDP protocol keyword.

    ```bash
    crackmapexec rdp <target_ip> -u admin -p password123
    ```

    Record which services return `[+]` (success) and which return `[-]` (failure). Credential reuse across all three services is a critical finding.

### Step 6: Enumerate Authenticated SMB Shares

!!! kali "List shares with credentials"
    With confirmed credentials, enumerate shares using an authenticated session to reveal any shares hidden from anonymous access.

    ```bash
    smbclient -L //<target_ip> -U admin%password123
    ```

    Authenticated listings often reveal shares that did not appear during anonymous enumeration.

!!! kali "Map authenticated share permissions"
    Map permissions on every share using `smbmap` with the validated credentials.

    ```bash
    smbmap -H <target_ip> -u admin -p password123
    ```

    Compare the authenticated share list against the anonymous listing from Step 4. Authenticated access often reveals additional shares or elevated permissions on shares that were read-only during anonymous enumeration.

---

### Record Your Findings

> **Nmap scan output:**
>
> ```
> (paste your nmap -sV -sC output here)
> ```
>
> **Open ports and services:**
>
> | Port | Service | Version |
> |------|---------|---------|
> |      |         |         |
> |      |         |         |
> |      |         |         |
>
> **enum4linux findings:**
>
> | Category | Details |
> |----------|---------|
> | Users    |         |
> | Shares   |         |
> | Groups   |         |
> | OS Info  |         |
>
> **CrackMapExec results:**
>
> | Protocol | Result | Admin Access? |
> |----------|--------|---------------|
> | SMB      |        |               |
> | SSH      |        |               |
> | RDP      |        |               |
>
> **Authenticated share permissions (smbmap):**
>
> | Share Name | Access Level |
> |------------|-------------|
> |            |             |
> |            |             |
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

### Step 7: Connect via SSH and Retrieve the Flag

!!! kali "Open an SSH session to the target"
    SSH provides the most direct path to command execution. Connect to the target using the validated credentials.

    ```bash
    ssh admin@<target_ip>
    ```

    Enter the password `password123` when prompted. A shell prompt confirms you are logged in on the target host.

!!! target "Read the flag file"
    Navigate to the flag location and read its contents from the target host.

    ```bash
    cat /tmp/private/flag.txt
    ```

    The flag is displayed in `OCR{...}` format. Copy the value and submit it on the platform.

### Step 8: Document Your Findings

A complete penetration test ends with structured documentation. Review everything you discovered and organize the findings by severity:

| Finding | Severity | Evidence |
|---------|----------|----------|
| Null session enumeration succeeds | High | `enum4linux -a` output shows users and shares |
| Guest mapping enabled (`map to guest = Bad User`) | High | Anonymous SMB connections succeed without valid credentials |
| Credential reuse across SMB, SSH, and RDP | Critical | CME shows `[+]` on all three protocols with `admin:password123` |
| Weak password on admin account | Critical | Password `password123` is trivially guessable |
| Sensitive data accessible via SSH | High | Flag file readable at `/tmp/private/flag.txt` |

Each finding should include the tool used, the exact command, the output received, and a remediation recommendation. The documentation phase transforms raw tool output into a professional deliverable.

---

## Analysis Questions

**1. Why should a penetration tester start with null session enumeration before attempting credential attacks?**

??? note "Reveal Answer"

    Null session enumeration gathers information without triggering authentication failure alerts. The user accounts, share names, and password policies discovered through null sessions help the tester build a targeted credential attack plan. Starting with credentials first risks account lockouts and generates logs that alert defenders. Null sessions reveal the attack surface while remaining as quiet as possible.

**2. What does the "map to guest = Bad User" setting reveal about the server's security configuration?**

??? note "Reveal Answer"

    The `map to guest = Bad User` setting means the server maps authentication attempts with invalid usernames to the guest account instead of rejecting them. The server never returns an "access denied" error for unknown users; it silently grants guest-level access. The configuration effectively disables username validation, allowing anyone to connect with any username and receive guest permissions. The setting is a significant misconfiguration because it masks failed authentication attempts and grants unintended access.

**3. How would you structure a penetration test report for the findings in this exercise?**

??? note "Reveal Answer"

    A professional report follows a standard structure: executive summary (non-technical overview for leadership), methodology (phases followed and tools used), findings (each vulnerability with severity, evidence, and remediation), and appendices (raw tool output). Each finding should include a description, risk rating, proof-of-concept steps, screenshots or command output, business impact, and specific remediation steps. The findings should be ordered by severity, with critical credential reuse and null session vulnerabilities listed first.

---

## Key Takeaways

- **Null session enumeration** is the first step in any Windows penetration test; the information gathered guides every subsequent attack
- **`map to guest = Bad User`** is a common SMB misconfiguration that grants guest access to any connection, regardless of the username provided
- **Credential reuse** across SMB, SSH, and RDP with the same `admin:password123` credentials demonstrates the catastrophic impact of weak, reused passwords
- **Structured methodology** ensures completeness; following the six phases (recon, enumeration, vulnerability identification, exploitation, post-exploitation, reporting) prevents missed findings
- **Documentation** transforms raw tool output into actionable intelligence; a penetration test without a report is just unauthorized access
- Exercise 9.3 is the **capstone of the Windows assessment track**, combining every technique from Chapters 1 through 9 into a single end-to-end penetration test
