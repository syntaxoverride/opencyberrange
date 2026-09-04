# Lab 2.3: SMB Anonymous Share Access

## Learning Objectives

- Access anonymous share and list files
- Understand SMB enumeration techniques
- Capture the flag

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before connecting.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify SMB service is running:**
   ```bash
   nmap -p 445 <target_ip>
   ```

### Step 2: Connect to Anonymous Share

Connect to the public SMB share using anonymous access (no credentials required).

**Detailed Steps:**

1. **Verify smbclient is installed:**
   ```bash
   which smbclient
   ```

2. **Connect to anonymous share:**
   ```bash
   smbclient //<target_ip>/public -N
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `//<target_ip>/public`: SMB share path (public share)
   - `-N`: No password flag (enables anonymous access)

3. **Expected connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

   **What this means:**
   - Connection was successful
   - You're now in the SMB client prompt
   - `smb: \>` indicates you're at the root of the share

**Troubleshooting:**
- If you get "Connection refused", verify IP and port 445
- If you get "NT_STATUS_BAD_NETWORK_NAME", try different share names: `public`, `share`, `files`
- If you get "NT_STATUS_ACCESS_DENIED", the share may require credentials

### Step 3: List Files

Explore the share to see what files are available.

**Detailed Steps:**

1. **List files and directories:**
   ```bash
   ls
   ```
   
   Type `ls` at the SMB prompt (`smb: \>`).

2. **Expected output:**
   ```
     .                                   D        0  Mon Jan 15 10:00:00 2024
     ..                                  D        0  Mon Jan 15 10:00:00 2024
     flag.txt                            A       45  Mon Jan 15 10:00:00 2024
     readme.txt                          A       123 Mon Jan 15 10:00:00 2024
   
                   524288 blocks of size 1024. 524288 blocks available
   ```

   **Output explanation:**
   - `.` and `..` are current and parent directories
   - `flag.txt` is the file we need (A = Archive/File, 45 = size in bytes)
   - `readme.txt` is another file
   - Last line shows disk space information

3. **Get detailed file information:**
   ```bash
   allinfo flag.txt
   ```

4. **Alternative: Use dir command:**
   ```bash
   dir
   ```
   
   `dir` is an alias for `ls` in smbclient.

### Step 4: Retrieve Flag

Download the flag file from the anonymous share.

**Detailed Steps:**

1. **Download the flag file:**
   ```bash
   get flag.txt
   ```
   
   Type `get flag.txt` at the SMB prompt.

2. **Expected output:**
   ```
   getting file \flag.txt of size 45 as flag.txt (0.3 KiloBytes/sec) (average 0.3 KB/s)
   ```

3. **Exit SMB client:**
   ```bash
   exit
   ```
   
   Or type `quit` to disconnect.

4. **Verify the file was downloaded:**
   ```bash
   ls -la flag.txt
   cat flag.txt
   ```

   **Expected flag content:**
   ```
   OCR{smb_4n0n_sh4r3}
   ```

**Troubleshooting:**
- If `get` fails, verify the filename is correct (case-sensitive)
- Check file permissions if download fails
- Use `pwd` to see current directory in SMB share

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_4n0n_sh4r3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Successfully connected to anonymous share using `smbclient` with `-N` flag
- ✅ Listed files in the share using `ls` command
- ✅ Located flag.txt in the file listing
- ✅ Downloaded flag.txt using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using -N flag
- Not listing files before downloading
- Incorrect share name

## Hints for Struggling Students

1. Use `smbclient //<target_ip>/public -N` to connect
2. Use `ls` to list files in the share
3. Use `get flag.txt` to download the flag

