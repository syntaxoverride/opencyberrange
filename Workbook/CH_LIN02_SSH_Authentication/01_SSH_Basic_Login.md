# Exercise L2.1: SSH Basic Login

## Before You Begin

- Confirm your VPN connection to the lab environment is active
- Open a terminal window on your attack machine
- Verify SSH is available by running `ssh -V`
- Have your notebook ready to record findings

## Scenario

You are conducting a penetration test for **FinanceCorp**, a mid-size financial services company. Your point of contact is **James Mitchell**, the IT Director. During the previous engagement phase, your team obtained a set of credentials through open-source intelligence gathering: `financecorp:Welcome2024#`. James has authorized you to test whether these credentials provide access to any of the company's Linux servers.

Your first objective is to authenticate to the target system using Secure Shell (SSH) and determine what information the server reveals upon login.

## Your Objectives

- Establish an SSH connection to the target using the provided credentials
- Read and analyze the Message of the Day (MOTD) displayed after login
- Identify system information disclosed in the MOTD banner
- Document all information the server reveals to an authenticated user
- Capture the flag embedded in the MOTD

---

## Background: The Message of the Day (MOTD)

When a user logs into a Linux system via SSH, the server can display a banner message before presenting the shell prompt. The MOTD is configured by system administrators to communicate maintenance windows, usage policies, or system status to legitimate users.

From a penetration tester's perspective, the MOTD is an intelligence source. Administrators often include details that help an attacker understand the environment:

- **Operating system and version**: reveals potential vulnerabilities
- **Hostname and domain**: maps the network topology
- **Last login time and source IP**: shows other active users
- **Installed services or roles**: identifies the server's purpose
- **Legal warnings**: confirm you are on a production system

Careless MOTD configurations can leak internal naming conventions, software versions, and infrastructure details that feed directly into the next phase of an engagement.

On most Linux distributions, the MOTD is controlled by files in `/etc/update-motd.d/` or the static file `/etc/motd`. Administrators who generate the MOTD dynamically (using scripts that pull system information at login time) are especially likely to disclose actionable details.

## Tool Primer: SSH Client

The `ssh` command establishes an encrypted connection to a remote system.

**Basic syntax:**

```bash
ssh <username>@<target_ip>
```

**Common flags:**

| Flag | Purpose |
|------|---------|
| `-p <port>` | Connect to a non-standard port |
| `-v` | Verbose output (useful for debugging) |
| `-i <keyfile>` | Specify a private key for authentication |
| `-o StrictHostKeyChecking=no` | Skip host key verification (lab use only) |

**Sample connection:**

```bash
ssh financecorp@10.10.10.5
```

After running the command, SSH prompts for a password. Type the password (characters will not appear on screen) and press Enter. A successful login displays the MOTD followed by a shell prompt.

**First-time connection note:** When connecting to a host for the first time, SSH asks you to verify the host key fingerprint. In a lab environment, type `yes` to accept and continue. In a production engagement, you would verify the fingerprint through an out-of-band channel.

---

## Walkthrough

### Step 1: Launch the Exercise

Navigate to **Exercises** then **Linux** then **Level 2**. Locate Exercise L2.1, click **Launch**, and wait for the status to show **Running**. Note the **target IP** displayed on the lab panel.

### Step 2: Connect via SSH

!!! kali "Authenticate over SSH"
    Open your terminal and initiate an SSH connection using the provided credentials. Replace `<target_ip>` with the address shown on the lab panel.

    ```bash
    ssh financecorp@<target_ip>
    ```

    If prompted to verify the host key, type `yes` and press Enter. When prompted for the password, type the credential below. The password will not echo to the screen; press Enter after typing it.

    ```
    Welcome2024#
    ```

    A successful login displays the MOTD banner followed by a shell prompt on the target.

### Step 3: Read the MOTD

Upon successful authentication, the server displays its MOTD banner before the shell prompt appears. Read the entire banner carefully. You should see output similar to:

```
*********************************************
*  Welcome to FinanceCorp Production Server *
*  Ubuntu 22.04 LTS - Financial Services    *
*  Hostname: fc-prod-web01                  *
*                                           *
*  Flag: OCR{________}                    *
*                                           *
*  Authorized access only.                  *
*********************************************
```

Do not skip past the banner. Every line contains information relevant to your engagement.

### Step 4: Extract System Information

!!! target "Confirm system details on the target"
    With the MOTD visible, identify each piece of disclosed information. Run the following commands inside the SSH session to confirm and expand on what the banner revealed.

    Check the hostname:

    ```
    hostname
    ```

    Check the operating system version:

    ```
    cat /etc/os-release
    ```

    Check the kernel version for additional vulnerability research:

    ```
    uname -a
    ```

    Check the current user context:

    ```
    whoami
    ```

    Check the last login record displayed by SSH:

    ```
    last -1 financecorp
    ```

    Each of these commands confirms or supplements the details the MOTD already disclosed. The kernel version from `uname -a` is particularly valuable; kernel exploits are a common privilege escalation path.

### Step 5: Review the MOTD Configuration

!!! target "Inspect the MOTD source on the target"
    Investigate how the MOTD is generated on the system. The first command lists the dynamic MOTD scripts; the second prints the static banner file.

    ```
    ls -la /etc/update-motd.d/
    ```

    ```
    cat /etc/motd
    ```

    Understanding where the MOTD comes from helps you determine whether it is static (manually written) or dynamic (generated by scripts at login). Dynamic MOTDs tend to leak more information because they pull live system data.

### Step 6: Document Your Findings

Before moving on, record every piece of information gathered. Accurate documentation during an engagement ensures nothing is lost between sessions.

### Record Your Findings

> **Login Details**
>
> | Field | Value |
> |-------|-------|
> | Target IP | __________ |
> | Username | __________ |
> | Password | __________ |
> | Login Successful? | Yes / No |
>
> **MOTD Information**
>
> | Detail | Value |
> |--------|-------|
> | Operating System | __________ |
> | Hostname | __________ |
> | Kernel Version | __________ |
> | Server Role | __________ |
> | Legal Warning Present? | Yes / No |
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** `OCR{____________}`

### Step 7: Record the Flag

Copy the flag in the `OCR{...}` format from the MOTD banner. Return to the lab platform and submit the flag in the designated field to complete Exercise L2.1.

### Step 8: Disconnect

!!! target "Close the SSH session"
    End your SSH session cleanly by running `exit` on the target.

    ```
    exit
    ```

    Verify the session has ended by confirming your terminal prompt has returned to your local machine.

---

## Analysis Questions

**1. Why do system administrators include detailed information in the MOTD, and how does an attacker benefit from it?**

??? note "Reveal Answer"

    Administrators configure the MOTD to help legitimate users identify which server they have connected to and to communicate maintenance schedules or usage policies. Attackers benefit because the banner reveals operating system versions, hostnames, server roles, and internal naming conventions; all of which inform further exploitation and lateral movement decisions.

**2. What is the security risk of displaying the operating system version in a login banner?**

??? note "Reveal Answer"

    Displaying the OS version allows an attacker to search for known vulnerabilities specific to that release. An Ubuntu 22.04 system, for example, has a defined set of CVEs that an attacker can cross-reference immediately after reading the banner, reducing the time needed to find a working exploit.

**3. How could an organization reduce information leakage from the MOTD without removing it entirely?**

??? note "Reveal Answer"

    Organizations can replace detailed system information with a generic legal warning that states unauthorized access is prohibited. Removing hostnames, OS versions, and server roles from the banner eliminates the intelligence value for attackers while still serving its purpose as a legal notice for legitimate users.

---

## Key Takeaways

- **MOTD banners are intelligence sources**: always read the full banner after every SSH login, as administrators frequently include system details that aid further exploitation
- **Password authentication over SSH** transmits credentials through an encrypted tunnel, but weak or reused passwords remain the primary risk
- **Hostname and OS version disclosure** allows attackers to narrow their vulnerability research to a specific platform and release
- **Kernel version information** from `uname -a` feeds directly into privilege escalation research, as kernel exploits bypass application-level controls entirely
- **Documentation during engagement** is critical; record every credential, hostname, and version string as you discover them
- **Clean disconnection** with `exit` ensures your session terminates properly and avoids leaving orphaned processes on the target
