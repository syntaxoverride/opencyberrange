# Exercise 2.2: SMB Share Listing

## Before You Begin

In Exercise 2.1, you connected to the SMB service and saw a basic share listing. this exercise presents a target with more shares; each one representing a different type of data that an organization might expose. Your job is to enumerate all of them, understand what the share names and types tell you, and assess the security implications.

Your VPN must be connected and your terminal open. You should be comfortable running `smbclient` from the previous exercise.

## Scenario

Your connection test to FinanceCorp's SMB service was successful. James Mitchell, the engagement lead, wants to know what shares are available and whether any sensitive information might be exposed through improperly configured shares. Your task is to produce a complete inventory of every share on the target and assess what each one might contain based on its name and type.

## Your Objectives

- List all SMB shares on the target using `smbclient -L`
- Understand share enumeration techniques and what the output reveals
- Identify all available shares and categorize them by type
- Capture the flag from the share listing output

---

## Background: Understanding Windows Share Types

Windows systems can have several categories of shares, and recognizing them quickly is an important skill during enumeration.

**Default/Administrative shares**: ADMIN$, C$, D$; are hidden by convention (the `$` suffix signals that the share should not appear in casual browse lists). These shares map directly to system drives and usually require administrative credentials to access.

**System shares**: IPC$ is the most common. It is always present on Windows systems and Samba servers. IPC$ is used for inter-process communication (RPC) and does not map to a folder on disk. You cannot browse it like a normal share, but it plays a role in further enumeration techniques covered in later chapters.

**User-created shares**: public, data, backup, HR, finance; are created by administrators for specific business purposes. Their names are chosen by the people who set them up, and those names often reveal their contents. A share named "backup" suggests copies of critical data. A share named "HR" suggests employee records. A share named "finance" suggests financial documents. The share name itself is intelligence.

Each share also has a **type**:

- **Disk**: a standard file system share that maps to a directory on the server
- **IPC**: an inter-process communication endpoint, not a browsable file share
- **Printer**: a shared printer resource

Understanding these categories helps you quickly sort through enumeration output and prioritize which shares deserve further investigation.

---

## Tool Primer: smbclient (Recap)

You used `smbclient` in Exercise 2.1 to connect to a single share. The same tool can list all shares on a target:

```bash
smbclient -L //<target_ip> -N
```

- `-L` tells smbclient to list shares instead of connecting to one
- `-N` suppresses the password prompt for anonymous (null session) access

Running this command on a target with more shares produces a richer listing. Where Exercise 2.1 showed one or two shares, this target has several; and each entry in the output includes a name, type, and comment field.

**Alternative tools** you may want to try after the main walkthrough:

- `enum4linux -S <target_ip>`: a wrapper script that automates SMB enumeration and formats the output differently
- `nmap --script smb-enum-shares -p 445 <target_ip>`: uses Nmap's scripting engine to discover shares, sometimes revealing details that smbclient does not

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** and locate Exercise 2.2; SMB Share Listing
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: List All Shares

!!! kali "Enumerate all SMB shares"
    Run the share listing command. Replace `<target_ip>` with the IP shown in the Active Lab View. The `-N` flag connects without a password so you can test for anonymous access.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    The output will look similar to this:

    ```
    Sharename       Type      Comment
    ---------       ----      -------
    public          Disk      Public file share
    data            Disk      Data share
    backup          Disk      OCR{<flag_here>}
    IPC$            IPC       IPC Service (Samba Server)
    ```

    Your output may differ slightly in formatting, but you should see four entries: three user-created shares and one system share.

### Step 3: Analyze Each Share

Go through the listing line by line. For each share, note three things: its name, its type, and its comment.

- **public**: Type: Disk. The name suggests content that was intentionally made available. The public share is likely the lowest-priority target for sensitive data, but it may still contain useful information.
- **data**: Type: Disk. A generic name that could contain anything. In a real engagement, a generic share name like this warrants investigation because it could hold anything.
- **backup**: Type: Disk. The name immediately stands out. Backups often contain complete copies of databases, configuration files, credentials, and other sensitive material. An attacker would prioritize this share. The comment field on this share contains the flag for this exercise. Note that comments are set by administrators and can contain any text; in a real engagement, comments sometimes reveal internal notes or descriptions.
- **IPC$**: Type: IPC. The IPC$ entry is a system share present on every SMB server. It is not a file share and cannot be browsed for documents. It exists for inter-process communication and is used by tools that perform deeper enumeration (such as querying user lists or group memberships).

### Step 4: Consider the Security Implications

You have not accessed any of these shares yet; you have only listed them. But the listing alone tells you a great deal:

- The organization has at least three distinct data repositories exposed over SMB
- One of them is explicitly named "backup," which signals high-value contents
- All of this information was available without any credentials (anonymous access)

In a real assessment, this share inventory would go directly into your report and would shape your next steps.

### Step 5: Record the Flag

The flag in `OCR{<flag_here>}` format appears in the comment field of the `backup` share. Copy it and paste it into the **Submit Flag** form on the platform.

### Step 6: (Optional) Try Alternative Tools

If you want to see how other tools present the same information, try these commands.

!!! kali "Enumerate shares with enum4linux"
    The `enum4linux -S` command produces a more verbose output that includes share information alongside other SMB details.

    ```bash
    enum4linux -S <target_ip>
    ```

!!! kali "Enumerate shares with the Nmap scripting engine"
    The `smb-enum-shares` script uses Nmap's scripting engine. The output format is different and may include additional details such as access permissions for each share.

    ```bash
    nmap --script smb-enum-shares -p 445 <target_ip>
    ```

Compare the output from all three tools. Each one presents the same underlying data in a different format, and different tools occasionally surface details that others miss.

---

## Record Your Findings

> Copy your full share listing output and paste it below.
>
> **My smbclient output:**
>
> ```
> (paste your output here)
> ```
>
> **Share analysis:**
>
> | Sharename | Type | Comment | What the name suggests | Security concern (Y/N) |
> |-----------|------|---------|------------------------|------------------------|
> |           |      |         |                        |                        |
> |           |      |         |                        |                        |
> |           |      |         |                        |                        |
> |           |      |         |                        |                        |

---

## Analysis Questions

**1. Three of the shares are user-created (public, data, backup) and one is a system share (IPC$). How can you tell the difference?**

??? note "Reveal Answer"

    IPC$ has the IPC type rather than the Disk type, and its name ends with the `$` suffix; a convention that marks system and administrative shares. The user-created shares have the Disk type and human-readable names chosen by an administrator. In a longer listing, you might also see ADMIN$ and C$, which follow the same `$` suffix convention for hidden system shares.

**2. A share named "backup" is visible to anonymous connections. Even if you cannot access its contents yet, why is this a finding worth reporting?**

??? note "Reveal Answer"

    The name alone reveals that backups exist and are hosted on this server. Backups often contain complete copies of databases, configuration files, and credentials. An attacker would prioritize attempting to access this share because a single successful connection could yield a large volume of sensitive data. The fact that the share name is visible without authentication means the organization is leaking information about its internal data storage practices.

**3. How would you use share names to plan the next phase of your assessment?**

??? note "Reveal Answer"

    Share names create a target priority list. "backup" likely contains the most sensitive information; full system or database copies; and should be tested first. "data" is a generic name that warrants investigation because it could hold anything. "public" might contain intentionally shared content with lower sensitivity, but should still be checked. Each share should be tested for anonymous access, and any that require credentials become targets for credential attacks in later chapters.

---

## Key Takeaways

- Share names are intelligence; they reveal what data the organization stores and where
- User-created shares (Disk type, no `$` suffix) are the primary targets for data access
- System shares (IPC$, ADMIN$, C$) serve specific purposes and are usually locked down
- Multiple tools can enumerate shares (smbclient, enum4linux, nmap scripts); different tools may reveal different details
- You now know what shares exist. The next step is testing whether you can actually access them; Exercise 2.3 explores anonymous share access
