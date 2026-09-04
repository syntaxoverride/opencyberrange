# Exercise 2.1: SMB Connection Test

## Before You Begin

Your Nmap scans in Chapter 1 found port 445 open and identified it as SMB. Until now, you have only observed the service from the outside; sending probes and reading responses. this exercise is the first time you will connect to a service and interact with it directly. You are moving from reconnaissance into active enumeration.

## Scenario

You are conducting a penetration test for FinanceCorp. During your initial enumeration in Chapter 1, you discovered SMB services running on their Windows server. The engagement lead, James Mitchell, wants to understand what information is exposed through SMB and whether anonymous access is permitted. Your job is to connect to the SMB service, list its shares, and report what you find.

## Your Objectives

- Connect to the SMB service on the target using smbclient
- Understand the basic smbclient connection syntax
- Test whether the server allows anonymous (no-password) access
- Identify the available shares and capture the flag

---

## Background: Your First Direct Service Connection

In Chapter 1, Nmap told you the door exists. Now you walk through it.

When you ran Nmap against port 445, you learned that SMB was listening. But a port scan only tells you that something is there; it does not tell you what is being shared, how the server is configured, or whether it requires credentials. To answer those questions, you need to connect to the service directly.

An SMB connection using smbclient gives you a list of available **shares** (shared folders and system resources) along with server information. Think of it like walking up to a building directory in a lobby; you can see which offices exist and read their posted descriptions before deciding which door to try.

The key concept in this exercise is **anonymous access**. The `-N` flag tells smbclient to connect without providing a password. If the server accepts this connection and returns its share listing, it means the server is configured to allow unauthenticated users to see what is available. Anonymous access is a significant finding in any penetration test.

What you see in a share listing:

- **Sharename**: the name of the shared resource
- **Type**: what kind of share it is (Disk, IPC, or Printer)
- **Comment**: a description set by the administrator

---

## Tool Primer: `smbclient`

Exercise 2.1 is your first time using smbclient. The tool is part of the **Samba suite**, a collection of tools that implement the SMB/CIFS networking protocol on Linux. While SMB is a Windows-native protocol, smbclient lets you interact with SMB servers from your Kali machine. It provides an FTP-like interface; you can list shares, browse directories, and transfer files.

**Basic listing syntax:**

```bash
smbclient -L //<target_ip> -N
```

The `smbclient -L -N` command connects to the target and asks it to list all available shares without providing any credentials.

**Flag breakdown:**

| Flag | Purpose |
|------|---------|
| `-L` | List the shares available on the target server |
| `-N` | No password; connect anonymously without prompting for credentials |
| `//<target_ip>` | The target address in UNC path format (two forward slashes followed by the IP) |

**Sample output:**

```
	Sharename       Type      Comment
	---------       ----      -------
	public          Disk      Public Files
	IPC$            IPC       IPC Service (FinanceCorp SMB - OCR{<flag_here>})
```

**Reading the columns:**

- **Sharename**: the name you would use to connect to that specific share. Share names like `public`, `data`, or `hr_documents` often reveal the purpose of the share and the structure of the organization.
- **Type**: the kind of resource being shared:
  - **Disk**: a file share, a directory on the server that has been made available over the network. These are the shares you will want to explore for files.
  - **IPC**: Inter-Process Communication, a system share used internally by Windows for administrative tasks and communication between processes. It appears on every SMB server.
  - **Printer**: a shared printer resource.
- **Comment**: a free-text description set by the server administrator. The comment field is optional, but administrators often use it to describe the share's purpose. Sometimes it contains server names, department information, or other details that are useful during a penetration test.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** → **Windows** → **Level 1**
- Click **Launch** on "SMB Connection Test"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Verify SMB Is Running

!!! kali "Confirm port 445 is open"
    Before connecting with smbclient, confirm that port 445 is open on the target. You already know how to do this from Chapter 1. The `-p 445` flag tells Nmap to scan only port 445 instead of the default 1,000 ports.

    ```bash
    nmap -p 445 <target_ip>
    ```

    You should see output confirming that port 445 is open:

    ```
    PORT    STATE SERVICE
    445/tcp open  microsoft-ds
    ```

    If the port shows as closed or filtered, the lab environment may not be fully started. Wait a moment and scan again.

### Step 3: Connect and List Shares

!!! kali "List SMB shares anonymously"
    Now use smbclient to connect to the SMB service and list available shares. The command connects anonymously and asks the server for its share listing.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    If the connection succeeds, you will see a table of shares with their names, types, and comments.

### Step 4: Read the Output

Examine the share listing carefully. For each share, note:

- The **name** of the share and what it might tell you about the server's purpose
- The **type**: is it a Disk share you could browse, or a system IPC share?
- The **comment** field; does it contain any useful information?

Look at the IPC$ share. The comment field for this share contains the flag in `OCR{...}` format.

### Step 5: Record the Flag

The flag is visible in the IPC$ comment field in `OCR{<flag_here>}` format.

Copy it and paste it into the **Submit Flag** form on the platform and click **Submit**.

---

## Record Your Findings

> **Nmap confirmation output:**
>
> ```
> (paste your nmap -p 445 output here)
> ```
>
> **smbclient share listing:**
>
> | Sharename | Type | Comment |
> |-----------|------|---------|
> |           |      |         |
> |           |      |         |
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

## Analysis Questions

**1. What is the IPC$ share and why does it appear on every SMB server?**

??? note "Reveal Answer"

    IPC$ is the Inter-Process Communication share. It is a system share created automatically by Windows and used for communication between processes, administrative tools, and null session enumeration. It cannot be removed or disabled; it exists on every machine running SMB, regardless of how the server is configured.

**2. The server comment in the IPC$ line contains the flag. In a real environment, what kind of information might appear in server comments?**

??? note "Reveal Answer"

    Administrator notes, the server's intended purpose, department names, internal hostnames, software versions, or other organizational information. Attackers use these details to map out the internal network structure, identify high-value targets, and craft more targeted attacks. Information that seems harmless to an administrator; like "HR File Server" or "backup-dc02"; gives an attacker context they would not otherwise have.

**3. You connected without providing any credentials. What does this tell you about the SMB server's configuration?**

??? note "Reveal Answer"

    Anonymous or guest access is enabled. The server accepted a connection with no username and no password and returned its full share listing. In a secure configuration, the server would reject connections that do not provide valid credentials, or at minimum restrict what information is returned to unauthenticated users. Unauthenticated share enumeration is a finding you would report to the client.

---

## Key Takeaways

- `smbclient -L` lists the shares available on an SMB server
- The `-N` flag connects without a password, testing for anonymous or guest access
- SMB shares have three types: Disk (file shares), IPC (system communication), and Printer
- Server comments and share descriptions often leak useful information about the organization and its infrastructure
- Now that you can connect and see what shares exist, the next exercise examines those shares in detail; what types they are and what their names reveal about the organization
