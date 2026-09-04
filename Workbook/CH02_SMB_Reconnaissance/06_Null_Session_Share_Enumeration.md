# Exercise 2.6: Null Session Share Enumeration

## Before You Begin

In Exercise 2.5, you established a null session and used `srvinfo` to pull basic server information. But null sessions can do much more. this exercise uses the same connection to enumerate shares through the RPC interface; and the results may reveal information that `smbclient -L` did not show.

Your VPN must be connected and your terminal open. You should be comfortable establishing a null session with `rpcclient` from the previous exercise.

## Scenario

Your null session connection to a FinanceCorp server was successful. James Mitchell, the engagement lead, wants to understand what information can be enumerated through null sessions, as this represents a significant security risk. Your task is to enumerate shares through the RPC interface and compare those results with what you found using `smbclient -L` earlier in the assessment.

## Your Objectives

- Enumerate shares using a null session and `rpcclient`
- Understand how RPC share enumeration differs from SMB share listing
- Capture the flag

---

## Background: Enumerating Shares Through RPC vs SMB

In Exercise 2.2, you listed shares using `smbclient -L`. That command uses the SMB protocol directly; it asks the server to list its available shares through the standard file-sharing interface.

Through a null session, you can list shares using RPC calls instead. The `netshareenum` command in `rpcclient` queries the Server Service (srvsvc) interface, which is a different pathway to the same information; but not always the same results.

RPC enumeration sometimes reveals additional details that `smbclient -L` does not show:

- **Physical paths**: the actual directory location on the server's file system (e.g., `/tmp/public` or `C:\Shares\data`)
- **Hidden shares**: shares that are configured to be invisible to SMB browse requests but still exist and respond to RPC queries
- **Extended comments**: remarks or descriptions set by the administrator that may contain sensitive details

The two methods complement each other. Always use both in an assessment. A share that appears in `smbclient -L` might show a different comment in `netshareenum`, and a share that is hidden from SMB browsing might still appear in RPC results.

Physical paths are particularly valuable. They reveal the directory structure on the server, which tells you about the operating system, how the administrator organizes data, and where interesting files might live outside the shared directories.

---

## Tool Primer: rpcclient Share Enumeration Commands

You already know how to establish a null session with `rpcclient` from Exercise 2.5. this exercise introduces three new commands for enumerating share information:

| Command | What It Returns |
|---------|----------------|
| `netshareenum` | Lists all shares with their types and comments |
| `netshareenumall` | Extended share listing (may include hidden shares) |
| `netsharegetinfo <sharename>` | Detailed info about a specific share including its physical path |

**Sample `netshareenum` output:**

```
netname: public
remark: Public file share
path:   /tmp/public
password:
netname: admin_backup
remark: OCR{example_flag_here}
path:   /tmp/admin_backup
password:
netname: IPC$
remark: IPC Service
path:   /tmp
password:
```

Each share entry includes a `netname` (the share name), a `remark` (the administrator's comment), a `path` (the physical location on disk), and a `password` field (almost always empty).

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** and locate Exercise 2.6; Null Session Share Enumeration
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Establish a Null Session

!!! kali "Establish a null session with rpcclient"
    Connect to the target using `rpcclient` with empty credentials:

    ```bash
    rpcclient -U "" -N <target_ip>
    ```

    Replace `<target_ip>` with the IP shown in the Active Lab View. You should see the `rpcclient $>` prompt, confirming the null session is established.

### Step 3: Enumerate Shares

!!! kali "Enumerate shares through RPC"
    Run the `netshareenum` command to list all shares:

    ```bash
    rpcclient $> netshareenum
    ```

    Review the output carefully. You should see three shares: `public`, `admin_backup`, and `IPC$`. Each entry includes the share name, a remark (comment), and the physical path on the server.

    Pay close attention to the remark field of the `admin_backup` share. It contains the flag in `OCR{<flag_here>}` format.

    Copy this value and paste it into the **Submit Flag** form on the platform.

### Step 4: Try Extended Enumeration

!!! kali "Run extended share enumeration"
    Run the extended share enumeration command:

    ```bash
    rpcclient $> netshareenumall
    ```

    Compare the output with what `netshareenum` returned. In some configurations, `netshareenumall` reveals additional shares; particularly administrative shares like `ADMIN$` or `C$`: that the standard enumeration does not include.

### Step 5: Get Detailed Share Information

!!! kali "Query detailed share information"
    Query detailed information about a specific share:

    ```bash
    rpcclient $> netsharegetinfo public
    ```

    Note the physical path returned. The path tells you exactly where on the server's file system the share is mapped. Repeat this for the other shares to build a picture of the server's directory layout.

### Step 6: Exit the Session

!!! kali "Disconnect the null session"
    Disconnect from the null session:

    ```bash
    rpcclient $> exit
    ```

### Step 7: Compare with smbclient

!!! kali "List shares over SMB for comparison"
    Run the standard SMB share listing for comparison:

    ```bash
    smbclient -L //<target_ip> -N
    ```

    Compare the shares, comments, and any differences in detail between this output and your `netshareenum` results. Note whether the comments match, whether any shares appear in one listing but not the other, and whether the RPC results provided information (like physical paths) that the SMB listing did not.

---

## Record Your Findings

> **netshareenum output:**
>
> ```
> (paste your netshareenum output here)
> ```
>
> **Share comparison:**
>
> | Share Name | smbclient Comment | rpcclient Comment | Physical Path |
> |------------|-------------------|-------------------|---------------|
> |            |                   |                   |               |
> |            |                   |                   |               |
> |            |                   |                   |               |
>
> **Flag value:** `______________________________`

---

## Analysis Questions

**1. Your `netshareenum` results included physical paths (like `/tmp/public`). Why is this information more valuable than just the share name?**

??? note "Reveal Answer"

    Physical paths reveal the directory structure on the server. An attacker learns where data is stored on disk, which helps identify the operating system, understand the file system layout, and plan post-exploitation activities. For example, seeing `/tmp/admin_backup` tells you the server is Linux-based and that backups are stored in a temporary directory; both details that inform further attack planning. Share names are labels; physical paths are blueprints.

**2. You used both `smbclient -L` and `netshareenum` to list shares. When might these two methods return different results?**

??? note "Reveal Answer"

    Some shares may be configured to be invisible to SMB browse lists but still enumerable via RPC. Administrative shares (`ADMIN$`, `C$`) may appear in RPC results but not in `smbclient` listings depending on configuration. Comments and descriptions can also differ between the two interfaces if they are set independently. The discrepancies are why a thorough assessment always uses both methods; each one can surface information the other misses.

**3. The admin_backup share is visible through enumeration. What does the name suggest about its contents, and why is this a security concern?**

??? note "Reveal Answer"

    The name suggests it contains administrative backups, which likely include system configurations, databases, user accounts, or credentials. Even if the share requires authentication to access, knowing it exists creates a high-priority target for credential attacks. An attacker now knows exactly which share to focus on after obtaining valid credentials; and the word "admin" in the name implies that its contents carry elevated privileges or sensitive system-level data.

---

## Key Takeaways

- `netshareenum` enumerates shares through the RPC interface via a null session
- RPC share enumeration can reveal physical paths and hidden shares that `smbclient -L` misses
- `netsharegetinfo` provides detailed information about individual shares, including their physical location on disk
- Always enumerate shares with both SMB (`smbclient -L`) and RPC (`netshareenum`) for complete coverage
- Share names tell you where data lives. The next exercise reveals something even more valuable: who has access to it; user enumeration through null sessions
