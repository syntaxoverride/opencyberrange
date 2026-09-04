# Exercise 9.1: Windows Network Assessment

## Before You Begin

Chapters 1 through 8 taught you to scan, enumerate, and attack individual services one at a time. Exercise 9.1 combines those techniques into a single assessment workflow; scanning all ports, enumerating every discovered service, and extracting data from misconfigurations. Make sure your VPN is connected and your Kali terminal is ready before launching the lab.

## Scenario

You are conducting the final phase of a penetration test for FinanceCorp. The engagement lead, James Mitchell, wants a thorough network assessment of a Windows server that combines all the techniques you have learned. Your goal is to identify every exposed service, enumerate access controls, and demonstrate data extraction from any misconfigured service. No credentials have been provided; everything you find must come from anonymous or guest-level access.

## Your Objectives

- Run a full port scan to identify all services on the target
- Enumerate SMB shares using anonymous and guest access
- Map share permissions to identify accessible resources
- Retrieve the flag from the HTTP service running on the target

---

## Background: Network Assessment Methodology

A network assessment follows a structured sequence of phases, each building on the findings of the previous one. Skipping a phase or testing services in random order leads to missed findings. The methodology ensures completeness and produces documentation that supports every conclusion in the final report.

The standard assessment phases are reconnaissance, enumeration, vulnerability identification, exploitation, and documentation. Reconnaissance identifies open ports and running services. Enumeration extracts detailed information from each service; versions, configurations, access controls, and exposed data. Vulnerability identification maps the enumerated information against known weaknesses. Exploitation confirms that the vulnerabilities are real by demonstrating impact. Documentation captures every step so the findings are reproducible.

```mermaid
graph LR
    A["Reconnaissance"] --> B["Enumeration"]
    B --> C["Vulnerability<br/>Identification"]
    C --> D["Exploitation"]
    D --> E["Documentation"]

    style A fill:#4a90d9,color:#fff
    style B fill:#4a90d9,color:#fff
    style C fill:#e8a735,color:#fff
    style D fill:#d9534f,color:#fff
    style E fill:#6aaa64,color:#fff
```

In Exercise 9.1, you will practice the first four phases. The target exposes three services: SMB on port 445, RDP on port 3389, and an nginx HTTP server on port 80. Guest access is enabled on the SMB service, and the HTTP server hosts a file containing the flag. No credentials are required for any step; guest and anonymous access are the vulnerabilities.

## Tool Primer: Anonymous SMB Access

SMB supports several authentication modes, and two of them require no credentials at all. A **null session** sends an empty username and password. A **guest session** authenticates as the built-in guest account. Both methods bypass normal access controls when the server is misconfigured to allow them.

!!! kali "List shares with a null session"
    A null session sends an empty username and password. Replace `<target_ip>` with the target shown in the Active Lab View.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    | Flag | Purpose |
    |------|---------|
    | `-L` | List available shares on the target |
    | `-N` | Use a null session (no password prompt) |

    A list of share names confirms the server accepts unauthenticated connections.

!!! kali "List shares as the guest user"
    A guest session authenticates as the built-in guest account when the server is misconfigured to allow it.

    ```bash
    smbclient -L //<target_ip> -U guest -N
    ```

    | Flag | Purpose |
    |------|---------|
    | `-U guest` | Authenticate as the guest user |
    | `-N` | Suppress the password prompt |

    If the share list returns, guest access is enabled and is a reportable finding.

!!! kali "Map share permissions with smbmap"
    The `smbmap` tool connects to the target and reports the access level for every share.

    ```bash
    smbmap -H <target_ip>
    ```

    The tool reports the access level (READ, WRITE, or NO ACCESS) for every share. When guest access is enabled, smbmap shows which shares an unauthenticated user can read or write to; a critical finding in any assessment.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** then **Windows** then **Level 2**
- Click **Launch** on "Windows Network Assessment"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Run a Full Service Scan

!!! kali "Full service and script scan"
    Start with a full service version scan to discover every open port and identify the software behind each service. The `-sV` flag probes each open port to determine the service name and version. The `-sC` flag runs Nmap's default NSE (Nmap Scripting Engine) scripts, which extract additional information like SMB share names, HTTP page titles, and protocol-specific metadata.

    ```bash
    nmap -sV -sC <target_ip>
    ```

    You should see three services in the output:

    ```
    PORT     STATE SERVICE       VERSION
    80/tcp   open  http          nginx
    445/tcp  open  microsoft-ds  ...
    3389/tcp open  ms-wbt-server ...
    ```

    Record every open port, service name, and version string. The scan results form the foundation for all subsequent enumeration.

### Step 3: Enumerate SMB Shares Anonymously

!!! kali "Enumerate SMB shares anonymously"
    Use `smbclient` with a null session to list all available shares on the target.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    The output lists every share name and its type. Look for non-default shares; names like `public`, `data`, or `files` indicate shares that administrators created and may have misconfigured. Default shares like `IPC$` and `ADMIN$` are present on every Windows SMB server and typically require authentication.

### Step 4: Map Share Permissions

!!! kali "Map share access levels"
    Run `smbmap` to determine your access level on each share.

    ```bash
    smbmap -H <target_ip>
    ```

    The output shows READ, WRITE, or NO ACCESS next to each share name. Any share showing READ or WRITE access without credentials is a significant finding. In a real assessment, you would document every accessible share and its permission level.

### Step 5: Access the Public Share

!!! kali "Connect to the public share"
    Connect to the accessible share and explore its contents.

    ```bash
    smbclient //<target_ip>/public -N
    ```

    Once connected, use `ls` to list files and `get <filename>` to download anything interesting. Guest-accessible shares often contain configuration files, internal documentation, or credentials stored in plaintext. Examine every file you find.

### Step 6: Run Full SMB Enumeration

!!! kali "Run full SMB enumeration"
    Use `enum4linux` to perform a thorough enumeration of the SMB service. The tool combines multiple SMB and RPC (Remote Procedure Call) queries into a single pass.

    ```bash
    enum4linux <target_ip>
    ```

    The output includes user accounts, group memberships, share listings, password policies, and OS (Operating System) information. Review the output for usernames, share details, and any configuration information that could support further attacks.

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
> **SMB shares discovered:**
>
> | Share Name | Access Level |
> |------------|-------------|
> |            |             |
> |            |             |
>
> **Files found on accessible shares:**
>
> ```
> (list files here)
> ```
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

### Step 7: Retrieve the Flag via HTTP

!!! kali "Retrieve the flag over HTTP"
    The Nmap scan revealed an nginx web server on port 80. Use `curl` to retrieve the flag file directly from the HTTP service. The command sends an HTTP GET request and prints the response body to your terminal.

    ```bash
    curl http://<target_ip>/flag.txt
    ```

    The flag is stored in `flag.txt` at the web root. Copy the flag value in `OCR{...}` format and submit it on the platform.

### Step 8: Interpret the Results

Review everything you have gathered and consider the full picture. The target exposes three services to the network. SMB allows guest access to at least one share. The HTTP server hosts sensitive files without any authentication. RDP is listening but has not been tested yet because no credentials are available.

In a professional assessment, each of these findings would be documented separately with a severity rating. Guest SMB access is a medium-to-high finding because it allows unauthenticated file access. An HTTP server hosting sensitive files without authentication is a high finding. The combination of multiple unauthenticated access paths elevates the overall risk rating for the target.

---

## Analysis Questions

**1. Why is guest access to SMB shares considered a critical misconfiguration?**

??? note "Reveal Answer"

    Guest access allows anyone on the network to read (and potentially write to) shared files without providing any credentials. Attackers can extract sensitive data, upload malicious files, or use the share as a staging area. The misconfiguration is especially dangerous because many organizations do not monitor guest-level SMB access, making it difficult to detect.

**2. How does retrieving the flag via HTTP complement the SMB enumeration findings?**

??? note "Reveal Answer"

    Discovering sensitive data on both SMB and HTTP demonstrates that the target has multiple unauthenticated access paths. The SMB finding shows a file-sharing misconfiguration, while the HTTP finding shows a web server misconfiguration. Together, they prove that the target lacks a consistent access control policy; the problem is systemic, not isolated to one service.

**3. Based on your findings, what would you recommend to FinanceCorp?**

??? note "Reveal Answer"

    Disable guest access on all SMB shares and require authentication for every connection. Remove sensitive files from the HTTP server's web root or place them behind authentication. Review the RDP configuration to ensure it requires strong credentials and Network Level Authentication (NLA). Implement network segmentation to limit which systems can reach these services.

---

## Key Takeaways

- **Guest access** on SMB shares allows unauthenticated users to list, read, and potentially write files; a critical misconfiguration that appears frequently in real environments
- **Full-service scanning** with `nmap -sV -sC` reveals all exposed services and their configurations in a single pass
- **Multiple unauthenticated access paths** (SMB guest access and HTTP without authentication) compound the risk; each finding alone is significant, but together they indicate systemic access control failures
- **No credentials were needed** to extract sensitive data from the target; misconfigurations can be as dangerous as weak passwords
- The next exercise, **Exercise 9.2**, introduces credential-based attacks against multiple services using CrackMapExec to test known credentials across SMB, RDP, and SSH
