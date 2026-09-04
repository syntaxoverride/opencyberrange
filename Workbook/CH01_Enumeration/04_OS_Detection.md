# Exercise 1.4: OS Detection

## Before You Begin

In Exercise 1.3, you identified the exact software running on each port. Version detection told you WHAT software is there. OS detection tells you WHAT platform it runs on; which narrows down which exploits, privilege escalation techniques, and post-exploitation tools apply. this exercise also introduces a new requirement: you need root privileges to run the scan. Your VPN must be connected and your terminal open.

## Scenario

Your reconnaissance of FinanceCorp is progressing. You have discovered open ports and identified service versions. Now you need to determine what operating system the target is running. Knowing the OS helps identify vulnerabilities specific to that platform and version; without it, you are guessing which tools and techniques to use next.

## Your Objectives

- Use Nmap OS detection (`-O`) to identify the target operating system
- Interpret the OS detection results including confidence percentage and CPE string
- Understand how OS fingerprinting works at a conceptual level
- Find and submit the flag

---

## Background: How Does OS Fingerprinting Work?

When Nmap performs OS detection, it does not ask the target "what OS are you?"; that would be too easy to fake. Instead, it sends specially crafted packets and analyzes how the target responds. Different operating systems implement TCP/IP slightly differently: they use different default **TTL** (Time To Live) values, **TCP window sizes**, **DF** (Don't Fragment) bit behavior, and **TCP options** ordering. These subtle differences create a "fingerprint" unique to each OS family and version.

```mermaid
graph LR
    A["Probes sent"] --> B["Responses analyzed"]
    B --> C["Fingerprint matched"]
    C --> D["OS identified"]
    style A fill:#4a90d9,color:#fff
    style B fill:#888,color:#fff
    style C fill:#d9a34a,color:#fff
    style D fill:#6aaa64,color:#fff
```

Nmap maintains a database of thousands of known OS fingerprints. After collecting responses, it compares the target's behavior against this database and returns the closest match along with a confidence percentage. The higher the confidence, the more closely the target matched a known signature. Firewalls, virtualization, or custom kernel configurations can alter responses and reduce confidence.

There is a practical reason this scan requires `sudo`: OS fingerprinting sends **raw network packets**: hand-crafted SYN, FIN, and other TCP packets that bypass the normal networking stack. Creating raw packets requires low-level access to the network interface. Version detection (`-sV`) only needs normal TCP connections that any user can create, but OS detection needs to go deeper.

## Tool Primer: `sudo nmap -O`

!!! kali "Run OS detection with root privileges"
    The OS detection scan adds the `-O` flag and requires root privileges:

    ```bash
    sudo nmap -O <target_ip>
    ```

    - **`-O`**: enables OS detection. Nmap sends fingerprinting probes and compares responses against its signature database
    - **`sudo`**: required because OS fingerprinting sends raw packets (crafted SYN, FIN, etc.) that need privileged access

**Additional useful flags:**

- **`--osscan-guess`**: guess more aggressively when the fingerprint does not exactly match any known signature
- **`--osscan-limit`**: skip OS detection on hosts without at least one open and one closed TCP port (Nmap needs both to fingerprint reliably)

**Reading the output:**

```
Nmap scan report for 10.100.5.10
PORT    STATE SERVICE
139/tcp open  netbios-ssn
445/tcp open  microsoft-ds

Device type: general purpose
Running: Microsoft Windows 2019
OS details: Microsoft Windows Server 2019
OS CPE: cpe:/o:microsoft:windows_server_2019
Network Distance: 1 hop
```

Key lines to focus on:

- **OS details**: Nmap's best guess at the exact operating system and version
- **OS CPE**: a Common Platform Enumeration identifier, a standardized naming scheme useful for cross-referencing vulnerabilities in databases like NVD
- **Network Distance**: how many hops away the target is (1 means same local network segment)
- **Confidence percentage**: how closely the target matched a known signature (e.g., 95% means a strong but not perfect match)

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform, navigate to the OS Detection lab, click **Launch**, and wait for the status to change to **Running**. Note the **target IP** displayed in the Active Lab View.

### Step 2: Verify Sudo Access

!!! kali "Verify sudo access"
    OS detection requires root privileges. Confirm you have them:

    ```bash
    sudo whoami
    ```

    The output should print `root`. If you receive a permissions error, resolve your access before continuing.

### Step 3: Run the OS Detection Scan

!!! kali "Run the OS detection scan"
    Run the scan with the `-O` flag:

    ```bash
    sudo nmap -O <target_ip>
    ```

    Replace `<target_ip>` with the IP shown in the Active Lab View. The OS detection scan takes slightly longer than a basic port scan because Nmap sends additional fingerprinting probes.

### Step 4: Interpret the Results

Examine the output and locate these key fields: the **OS details** line (the exact version string), the **confidence percentage** (anything above 90% is a strong match), the **CPE string** (a standardized identifier for vulnerability database lookups), and the **Network Distance** (number of hops to the target).

Note that this exercise runs Linux with Samba configured to simulate a Windows environment. Nmap may report Linux or Windows depending on the configuration. The ambiguity is realistic; in real engagements, virtualization and service emulation can make OS detection uncertain.

### Step 5: Find the Flag

!!! kali "Read the flag from the SMB server string"
    The target advertises the flag inside its SMB server string. List the shares with `smbclient` and no password (`-N`); the server string appears in the IPC$ comment at the bottom of the listing:

    ```bash
    smbclient -L //<target_ip> -N
    ```

    Look for the `OCR{<flag_here>}` value in the server string shown alongside the share listing. The same string also appears in the version-scan banner:

    ```bash
    nmap -sV -p 445 <target_ip>
    ```

    Paste the flag value into the **Submit Flag** form on the platform and click **Submit**.

---

### Record Your Findings

> Record the key details from your OS detection scan below.
>
> | Field | Your Finding |
> |-------|-------------|
> | OS detected | |
> | Confidence % | |
> | CPE string | |
> | Network distance | |
> | Additional notes | |
>
> **Flag found:**
>
> ```
> (paste your flag here)
> ```

---

## Analysis Questions

**1. Why does OS detection require root privileges when version detection (`-sV`) does not?**

??? note "Reveal Answer"

    OS fingerprinting sends raw network packets; hand-crafted SYN, FIN, and other TCP segments that bypass the normal networking stack. Creating raw packets requires privileged access to the network interface. Version detection uses normal TCP connections that any unprivileged user can create. The difference is between talking through the OS networking layer (normal) and directly manipulating packets on the wire (privileged).

**2. The scan reports the OS with 95% confidence. What does the remaining 5% uncertainty mean?**

??? note "Reveal Answer"

    OS fingerprinting is probabilistic. The target's TCP/IP behavior matched a known signature closely but not perfectly. Firewalls, custom kernel configurations, or virtualization can alter probe responses, shifting the fingerprint away from the canonical signature. The remaining uncertainty means another OS could theoretically produce similar responses, or the target's environment has modified its network behavior.

**3. How would knowing the exact OS version change your approach to the rest of a penetration test?**

??? note "Reveal Answer"

    The OS version determines which exploits are viable (a Windows exploit will not work on Linux, and a Windows 10 exploit may not work on Server 2019), which privilege escalation techniques apply, which post-exploitation tools to deploy, and what default configurations to expect. Without OS information you are working blind; with it, you can focus on the attack surface that actually exists.

---

## Key Takeaways

- OS fingerprinting (`-O`) analyzes TCP/IP stack behavior to identify the target operating system
- It requires **root privileges** (`sudo`) because it sends raw network packets that bypass the normal networking stack
- The output includes an OS guess, a confidence percentage, and a CPE identifier that can be used for vulnerability lookups
- OS information narrows down which exploits, privilege escalation paths, and post-exploitation tools are relevant to the target
- You now have individual techniques for port scanning, version detection, and OS fingerprinting. The next exercise combines all of them into a single unified scan.
