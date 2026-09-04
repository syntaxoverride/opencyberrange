# Exercise 8.1: Single Service Credential Discovery

## Before You Begin

Credential discovery exercises test whether known or guessed credentials grant access to network services. Before starting the lab, confirm that your Kali Linux virtual machine (VM) is connected to the OpenCyberRange environment through the WireGuard VPN tunnel. You should be able to reach the lab target at its assigned IP address before proceeding.

Make sure you have the following tools available on your Kali VM:

- `nmap` for port scanning and service enumeration
- `smbclient` for interacting with Server Message Block (SMB) shares
- `smbmap` for enumerating share permissions

## Scenario

FinanceCorp has engaged your team for a penetration test of internal network services. James Mitchell, the company's IT security lead, suspects that weak or default credentials may be in use across the environment. Your first task is to test a discovered set of credentials; `admin:password123`: against an SMB file-sharing service running on a target host.

The target server exposes SMB on port 445 and hosts two file shares: `share1` and `share2`. Your goal is to authenticate with the provided credentials, enumerate all available shares, and determine what sensitive data can be accessed.

## Your Objectives

Each objective maps to a phase of the credential testing process.

1. Scan the target to confirm SMB is running on port 445
2. Authenticate to the SMB service using the provided credentials
3. List and explore all available shares
4. Retrieve any sensitive files, including the flag
5. Document your findings for the engagement report

---

## Background: Credential Discovery

Credential discovery is the process of identifying valid username and password combinations that grant access to a target system or service. Attackers obtain credentials through many methods; phishing, password spraying, database breaches, or default credential lookups. Once a valid credential pair is found, the next step is determining what level of access the credentials provide.

Single-service credential testing focuses on one protocol at a time. A penetration tester authenticates against a specific service, such as SMB, and then enumerates what resources are available under that account. The value of single-service testing lies in understanding the blast radius of a compromised credential before moving on to cross-service reuse checks.

```mermaid
flowchart LR
    A["Obtain<br/>Credentials"] --> B["Identify<br/>Target Service"]
    B --> C["Authenticate<br/>to Service"]
    C --> D["Enumerate<br/>Resources"]
    D --> E["Extract<br/>Sensitive Data"]

    style A fill:#4a90d9,stroke:#333,color:#fff
    style B fill:#4a90d9,stroke:#333,color:#fff
    style C fill:#e8a735,stroke:#333,color:#fff
    style D fill:#e8a735,stroke:#333,color:#fff
    style E fill:#d9534f,stroke:#333,color:#fff
```

SMB is a network file-sharing protocol commonly found in corporate environments. Samba is the open-source implementation of SMB used on Linux systems. When SMB shares are protected only by weak credentials, an attacker who obtains those credentials can read, download, or modify files across the network.

## Tool Primer: smbclient

The `smbclient` utility provides a command-line interface for interacting with SMB shares, similar to how an FTP (File Transfer Protocol) client interacts with FTP servers. Penetration testers use `smbclient` to list available shares, browse directories, and retrieve files from remote hosts.

The following table summarizes the key `smbclient` operations used in this exercise.

| Operation | Command | Description |
|-----------|---------|-------------|
| List shares | `smbclient -L //<target_ip> -U admin%password123` | Display all shares on the target |
| Connect to share | `smbclient //<target_ip>/share1 -U admin%password123` | Open an interactive session on a share |
| List files | `ls` | List files in the current directory |
| Read a file | `more filename` | Display file contents in the terminal |
| Download a file | `get filename` | Download a file to the local machine |
| Exit session | `exit` | Close the smbclient session |

The `-U` flag accepts credentials in the format `username%password`. When the connection succeeds, `smbclient` drops into an interactive prompt where you can browse the share like a local filesystem.

## Walkthrough

### Step 1: Launch the Exercise

Open the OpenCyberRange dashboard and navigate to the Credential Reuse track. Start Exercise 8.1 and wait for the environment to report a ready status. Note the target IP address displayed on the lab panel; all subsequent commands will use the target IP shown in your environment.

!!! kali "Confirm connectivity to the target"
    Send a ping to the target IP shown on the lab panel to verify the path is up before running any tools.

    ```bash
    ping -c 3 <target_ip>
    ```

    A successful reply confirms that your VPN tunnel is active and the lab containers are running.

### Step 2: Scan Port 445

!!! kali "Scan port 445 for SMB"
    Run an Nmap service version scan against port 445 to confirm that SMB is active and to identify the Samba version running on the target.

    ```bash
    nmap -sV -p 445 <target_ip>
    ```

    The output should show port 445 as open with a Samba service banner. Note the version string; version information is useful for identifying known vulnerabilities in later assessments.

### Step 3: List SMB Shares with Credentials

!!! kali "List SMB shares with credentials"
    Use `smbclient` with the `-L` flag to list all available shares on the target. Authenticate with the credentials `admin:password123`.

    ```bash
    smbclient -L //<target_ip> -U admin%password123
    ```

    The output displays each share name, its type, and an optional comment. Look for non-default shares beyond the standard `IPC$` and `print$` entries. You should see two custom shares: `share1` and `share2`.

!!! kali "Verify share permissions with smbmap"
    Confirm what the authenticated user can read or write by running `smbmap` against the same target.

    ```bash
    smbmap -H <target_ip> -u admin -p password123
    ```

    The `smbmap` output shows read and write permissions for each share, giving you a quick overview of what the authenticated user can access.

### Step 4: Explore share1

!!! kali "Connect to and browse share1"
    Connect to `share1` using `smbclient` and browse the contents.

    ```bash
    smbclient //<target_ip>/share1 -U admin%password123
    ```

    Once connected, list the files in the share at the interactive prompt.

    ```
    smb: \> ls
    ```

    Read any files you find using the `more` command.

    ```
    smb: \> more <filename>
    ```

    Review the contents carefully. Files in `share1` may contain notes, configuration details, or other information relevant to the engagement. Exit the session when you have finished reviewing.

    ```
    smb: \> exit
    ```

### Step 5: Explore share2 and Find the Flag

!!! kali "Connect to share2 and find the flag"
    Connect to `share2` and examine its contents.

    ```bash
    smbclient //<target_ip>/share2 -U admin%password123
    ```

    List the files in the share at the interactive prompt.

    ```
    smb: \> ls
    ```

    You should see a file named `flag.txt`. Read the flag file using the `more` command.

    ```
    smb: \> more flag.txt
    ```

    The file contains the flag in `OCR{...}` format. Copy the flag value exactly as displayed; you will submit the flag in a later step. Exit the session.

    ```
    smb: \> exit
    ```

---

### Record Your Findings

Document the results of your scan and SMB enumeration below.

> **My Nmap output:**
>
> ```
> (paste your nmap output here)
> ```
>
> **My smbclient share listing:**
>
> ```
> (paste your smbclient -L output here)
> ```
>
> **Open ports I found:**
>
> | Port | Service |
> |------|---------|
> |      |         |
>
> **Shares I found:**
>
> | Share Name | Permissions | Notable Files |
> |------------|-------------|---------------|
> |            |             |               |
>
> **Flag value:**
>
> ```
> (paste the flag here)
> ```

---

### Step 6: Interpret the Results

Review what the credential test revealed about the target environment. The credentials `admin:password123` granted access to the SMB service and provided read access to at least two file shares. One of those shares contained a file with sensitive data; the flag.

Consider what the findings mean from a risk perspective. Weak credentials on a file-sharing service allow an attacker to exfiltrate documents, configuration files, and other sensitive material. The fact that the same account has access to multiple shares increases the impact of the compromise.

### Step 7: Find and Submit the Flag

Return to the OpenCyberRange dashboard and paste the `OCR{...}` flag value into the submission field for Exercise 8.1. The platform validates the flag against the expected value stored in the lab configuration. A successful submission confirms that you completed the full credential discovery workflow.

---

## Analysis Questions

Work through each question to reinforce the concepts covered in the lab.

**1. Why is it important to check all available shares, not just the first one you find?**

??? note "Reveal Answer"

    Different shares may have different access controls and contain different categories of data. An attacker who stops after finding one accessible share may miss the most sensitive files on the system. Thorough enumeration ensures that the full scope of exposure is documented in the penetration test report.

**2. What does a successful SMB authentication tell you about the target environment?**

??? note "Reveal Answer"

    Successful authentication confirms that the credentials are valid for the SMB service and that the account has not been disabled or locked out. The result also indicates that the SMB service does not enforce additional access controls such as IP-based restrictions or multi-factor authentication (MFA). From a defensive standpoint, the organization should audit password policies and enforce stronger credential requirements.

**3. How would you report this finding in a penetration test engagement?**

??? note "Reveal Answer"

    The report should document the credential pair used, the service and port tested, the shares accessible, and the specific files retrieved. The finding should be classified by severity based on the sensitivity of the data exposed. A recommendation section should advise the client to rotate the compromised credentials, enforce minimum password complexity requirements, and review share-level access controls.

---

## Key Takeaways

The credential testing methodology follows a structured sequence: obtain credentials, identify the target service, authenticate, enumerate resources, and extract data. Each phase builds on the previous one and contributes to a complete picture of the compromise.

Always enumerate all available resources after authentication. Stopping at the first share or first accessible file leaves gaps in the assessment. A thorough tester examines every share, directory, and file within the authenticated session.

The `smbclient` utility is a versatile tool for SMB interaction. Listing shares with `-L`, connecting to individual shares, and using commands like `ls`, `more`, and `get` covers the majority of SMB enumeration tasks during a penetration test.

Exercise 8.2 builds on the credential discovery process by testing whether the same credentials work on additional services; a technique known as cross-service credential reuse.
