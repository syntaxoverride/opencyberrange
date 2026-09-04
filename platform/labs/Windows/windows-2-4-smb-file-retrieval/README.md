# Lab 2.4: SMB File Retrieval

## Learning Objectives

- Download file from anonymous SMB share
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

### Step 2: Connect to Share

Connect to the public SMB share using anonymous access.

**Detailed Steps:**

1. **Verify smbclient is installed:**
   ```bash
   which smbclient
   ```

2. **Connect to public share:**
   ```bash
   smbclient //<target_ip>/public -N
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `//<target_ip>/public`: SMB share path
   - `-N`: No password flag (anonymous access)

3. **Expected connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

4. **Verify you're connected:**
   ```bash
   pwd
   ```
   
   Should show current directory in the share.

### Step 3: List Files and Locate Flag

Before downloading, list files to confirm flag.txt exists.

**Detailed Steps:**

1. **List files in the share:**
   ```bash
   ls
   ```
   
   Type `ls` at the SMB prompt.

2. **Expected output:**
   ```
     .                                   D        0  Mon Jan 15 10:00:00 2024
     ..                                  D        0  Mon Jan 15 10:00:00 2024
     flag.txt                            A       45  Mon Jan 15 10:00:00 2024
   
                   524288 blocks of size 1024. 524288 blocks available
   ```

3. **Verify flag.txt is present:**
   - Look for `flag.txt` in the listing
   - Note the file size (45 bytes in this example)

### Step 4: Download Flag File

Download the flag file from the SMB share to your local machine.

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

   **What this means:**
   - File was successfully downloaded
   - Original file: `\flag.txt` (on SMB share)
   - Downloaded as: `flag.txt` (on your local machine)
   - Transfer speed: 0.3 KB/s

3. **Alternative: Download to specific location:**
   ```bash
   get flag.txt /tmp/flag.txt
   ```
   
   This downloads the file to `/tmp/flag.txt` instead of current directory.

4. **Verify download was successful:**
   ```bash
   !ls -la flag.txt
   ```
   
   The `!` prefix runs the command on your local machine, not the SMB share.

### Step 5: Exit and View Flag

Exit the SMB client and view the downloaded flag file.

**Detailed Steps:**

1. **Exit SMB client:**
   ```bash
   exit
   ```
   
   Or type `quit` or `q` to disconnect.

2. **Verify you're back in your local shell:**
   ```bash
   pwd
   ```
   
   Should show your local directory, not the SMB prompt.

3. **View the flag file:**
   ```bash
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{smb_f1l3_r3tr13v3}
   ```

4. **Alternative viewing methods:**
   ```bash
   # View with less (for longer files)
   less flag.txt
   
   # View first few lines
   head flag.txt
   
   # View with line numbers
   cat -n flag.txt
   ```

5. **Verify file was downloaded correctly:**
   ```bash
   ls -la flag.txt
   file flag.txt
   ```

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_f1l3_r3tr13v3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters
- ✅ File was successfully downloaded and readable

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Successfully connected to public share using `smbclient` with `-N` flag
- ✅ Listed files in the share and located flag.txt
- ✅ Downloaded flag.txt using `get` command
- ✅ Exited SMB client successfully
- ✅ Viewed flag content using `cat flag.txt`
- ✅ Verified flag format is correct: `OCR{...}`

**Key SMB Commands Reference:**
- `ls` or `dir`: List files
- `get <file>`: Download a file
- `put <file>`: Upload a file
- `cd <dir>`: Change directory
- `pwd`: Print current directory
- `exit` or `quit`: Exit SMB client
- `!<command>`: Run command on local machine

## Common Mistakes

- Not using get command correctly
- Forgetting to exit before viewing file
- Not specifying correct filename

## Hints for Struggling Students

1. Connect with `smbclient //<target_ip>/public -N`
2. Use `get flag.txt` to download
3. Exit with `exit` and view with `cat flag.txt`

