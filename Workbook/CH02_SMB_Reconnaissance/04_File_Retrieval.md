# Exercise 2.4: File Retrieval

## Before You Begin

In Exercise 2.3, you connected to an anonymous share and browsed its contents. You saw file names and directories; but seeing a file name and having the file on your machine are two different things. In a penetration test, downloading files is how you prove impact. this exercise focuses on the mechanics of extracting files from SMB shares.

Your VPN must be connected and your terminal open. You should be comfortable connecting to SMB shares and navigating them interactively from the previous exercise.

## Scenario

Your SMB assessment of FinanceCorp has confirmed that anonymous access to certain shares is possible. James Mitchell, the engagement lead, wants to understand the full impact by seeing what files can actually be retrieved. Listing files proves visibility; downloading them proves exposure. Your task is to download files from the anonymous share and demonstrate what an attacker could walk away with.

## Your Objectives

- Download a file from an anonymous SMB share using `smbclient`
- Understand the difference between interactive and non-interactive file retrieval
- Capture the flag from the downloaded file

---

## Background: From Browsing to Exfiltration

In a penetration test report, "the share was accessible" is a finding. "Here is the data I downloaded" is proof. Both matter, but they carry different weight.

Browsing a share tells you what exists. Downloading files demonstrates real-world impact; it shows that an attacker with the same level of access could exfiltrate that data. A file listing says "this data is visible." A downloaded file says "this data is now in someone else's hands."

`smbclient` provides two approaches for downloading files. The first is **interactive mode**, where you connect to the share, navigate its contents, and use download commands within the session. The second is a **non-interactive one-liner** using the `-c` flag, which runs a command and exits immediately; useful for scripting and for documenting reproducible proof-of-concept commands in your report.

One detail that catches beginners off guard: downloaded files land in your **current working directory**: wherever you were in your local file system when you ran `smbclient`. If you launched `smbclient` from your home directory, the files appear in your home directory. If you launched it from `/tmp`, they land in `/tmp`. Keep this in mind when organizing your assessment output.

---

## Tool Primer: File Download Commands

You already know how to connect to a share and list its contents from Exercise 2.3. this exercise extends that knowledge with download-focused commands.

**Interactive download commands** (used inside an smbclient session):

- `get <remote_file>`: download a single file to your current working directory
- `get <remote_file> <local_name>`: download a file and save it with a different local name
- `mget <pattern>`: download multiple files matching a pattern (e.g., `mget *.txt`)
- `prompt`: toggle the per-file confirmation prompt for `mget` (turn it off for bulk downloads)
- `lcd <local_dir>`: change the local directory where downloaded files will be saved

**Non-interactive one-liner:**

```bash
smbclient //<target_ip>/public -N -c 'get flag.txt'
```

The `-c` flag tells `smbclient` to execute the specified command and then exit. The non-interactive form is the approach you would use when scripting downloads across multiple targets or when you want a single command you can paste into a report as a proof of concept.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** and locate Exercise 2.4; File Retrieval
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Connect to the Share

!!! kali "Connect to the public share"
    Connect to the public share using anonymous access. Replace `<target_ip>` with the IP shown in the Active Lab View.

    ```bash
    smbclient //<target_ip>/public -N
    ```

    You should see the `smb: \>` prompt, indicating a successful connection.

### Step 3: List the Contents

!!! kali "List the share contents"
    Confirm what files are available on the share.

    ```bash
    smb: \> ls
    ```

    You should see `flag.txt` in the listing. Note its size; 45 bytes. In a real engagement, you would document every file and directory you can see before downloading anything.

### Step 4: Download the File

!!! kali "Download the flag file"
    Download `flag.txt` to your local machine.

    ```bash
    smb: \> get flag.txt
    ```

    `smbclient` will confirm the download with a message showing the number of bytes transferred. The file is now on your machine, in whatever directory you were in when you launched `smbclient`.

### Step 5: Exit the Session

!!! kali "Disconnect from the share"
    Disconnect from the share.

    ```bash
    smb: \> exit
    ```

### Step 6: Read the Downloaded File

!!! kali "Read the downloaded file"
    Back at your local terminal prompt, read the file you just downloaded.

    ```bash
    cat flag.txt
    ```

    The file contains the flag in `OCR{<flag_here>}` format.

Copy this value and paste it into the **Submit Flag** form on the platform.

### Step 7: (Alternative) Non-Interactive Method

!!! kali "Download the file with a one-liner"
    You can accomplish the same result with a single command that does not require an interactive session. The `smbclient -c` one-liner connects to the share, downloads the file, and exits.

    ```bash
    smbclient //<target_ip>/public -N -c 'get flag.txt'
    ```

    Verify the download the same way:

    ```bash
    cat flag.txt
    ```

The one-liner approach is useful when you already know the exact file you want, when you are scripting downloads across multiple targets, or when you need a clean, reproducible command for your report.

---

## Record Your Findings

> **File listing from the share:**
>
> ```
> (paste your ls output here)
> ```
>
> **Downloaded files:**
>
> | Filename | Size | Contents / Notes |
> |----------|------|------------------|
> |          |      |                  |
>
> **Flag value:** `______________________________`

---

## Analysis Questions

**1. What is the difference between listing a file in a share and downloading it? Why does a penetration test report need both?**

??? note "Reveal Answer"

    Listing proves the file exists and is visible to anyone with the same level of access. Downloading proves the data can be exfiltrated; that an attacker could take a copy and leave. A report that includes both shows the vulnerability (files are visible without credentials) and the impact (the actual data is exposed and retrievable). Listing is the finding; downloading is the evidence.

**2. When would you use the non-interactive `-c` flag instead of connecting interactively?**

??? note "Reveal Answer"

    When you know exactly what you want; a specific filename on a specific share; there is no reason to open an interactive session. The `-c` flag is also the better choice when scripting downloads across multiple targets, when automating data collection, or when documenting a reproducible proof-of-concept command for a report. A reviewer can copy and paste a single one-liner to verify your finding.

**3. You downloaded a 45-byte text file. In a real environment, what types of files would make this vulnerability critical?**

??? note "Reveal Answer"

    Database backups, configuration files containing credentials, SSH private keys, password files, financial records, customer PII, source code, internal documentation with network diagrams, and API keys or tokens. Any file whose exposure causes regulatory, financial, or reputational damage transforms this from a low-severity misconfiguration into a critical finding. The vulnerability is the same; anonymous read access; but the impact depends entirely on what the share contains.

---

## Key Takeaways

- `get` downloads a single file; `mget` downloads multiple files matching a pattern
- Downloaded files land in your current working directory; use `lcd` inside the session to change the local destination
- The `-c` flag provides a non-interactive one-liner for scripting and documentation
- Downloading files is how you prove impact in a penetration test; it turns a finding into evidence
- You have now completed the anonymous access portion of SMB reconnaissance: connecting, listing, browsing, and downloading. The next exercise introduces a different technique; null sessions; which reveals information that anonymous file access cannot
