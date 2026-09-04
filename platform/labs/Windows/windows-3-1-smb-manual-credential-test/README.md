# Lab 3.1: SMB Manual Credential Test

## Learning Objectives
- Manually test one username/password combination
- Understand SMB authentication
- Capture the flag

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

### Step 2: Verify SMB Service

Confirm that SMB service (port 445) is accessible before attempting authentication.

**Detailed Steps:**

1. **Quick port check:**
   ```bash
   nmap -p 445 <target_ip>
   ```

   **Expected output:**
   ```
   PORT    STATE SERVICE
   445/tcp open  microsoft-ds
   ```

2. **Verify SMB is responding:**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   This lists available shares without authentication.

   **Expected output:**
   ```
   Sharename       Type      Comment
   ---------       ----      --------
   private         Disk      
   IPC$            IPC       IPC Service (Samba 4.15.13-Ubuntu)
   ```
   
   **Note:** You may see a warning about SMB1 protocol negotiation. This is normal and can be ignored. The important part is that you can see the `private` share listed.

### Step 3: Connect with Credentials

Connect to the private SMB share using the provided credentials.

**Detailed Steps:**

1. **Connect to private share with username:**
   ```bash
   smbclient //<target_ip>/private -U admin
   ```
   
   Replace `<target_ip>` with your actual target IP

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `//<target_ip>/private`: SMB share path (private share)
   - `-U admin`: Specify username as "admin"

2. **Enter password when prompted:**
   ```
   Enter WORKGROUP\admin's password:
   ```
   
   Type: `password` (then press Enter)
   
   **Note:** The password will not be visible as you type (this is normal for security).

3. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

   **What this means:**
   - Authentication was successful
   - You're now connected to the private share
   - `smb: \>` is the SMB prompt

4. **Alternative: Provide password in command (less secure):**
   ```bash
   smbclient //<target_ip>/private -U admin%password
   ```
   
   The `%` separates username from password. This avoids the password prompt.

**Troubleshooting authentication:**
- **"NT_STATUS_LOGON_FAILURE"**: Wrong username or password
  - Verify username: `admin` (case-sensitive)
  - Verify password: `password` (case-sensitive)
  - Make sure you're using `-U admin` to specify the username
- **"NT_STATUS_BAD_NETWORK_NAME"**: Share name might be wrong
  - Try: `private`, `Private`, `PRIVATE`
  - Make sure you're connecting to `//<target_ip>/private` (not `/public`)
- **"NT_STATUS_ACCESS_DENIED"**: Credentials correct but insufficient permissions
  - Try different username/password combinations if provided
- **Connection timeout**: Check IP address and network connectivity
- **SMB1 protocol warnings**: These are normal and can be ignored - the connection will still work

### Step 4: Verify Connection and List Files

Confirm you're connected and can access files in the private share.

**Detailed Steps:**

1. **Check current directory:**
   ```bash
   pwd
   ```

2. **List files in the share:**
   ```bash
   ls
   ```

   **Expected output:**
   ```
     .                                   D        0  Mon Jan 15 10:00:00 2024
     ..                                  D        0  Mon Jan 15 10:00:00 2024
     flag.txt                            A       45  Mon Jan 15 10:00:00 2024
   
                   524288 blocks of size 1024. 524288 blocks available
   ```

   **Output explanation:**
   - `flag.txt` is the file we need
   - `A` = Archive attribute (regular file)
   - `45` = file size in bytes

3. **If flag is in a subdirectory:**
   ```bash
   cd <directory_name>
   ls
   ```

### Step 5: Retrieve Flag

Download the flag file from the private share.

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
   OCR{smb_m4nu4l_4uth}
   ```

**Alternative download methods:**
- Download to specific location: `get flag.txt /tmp/flag.txt`
- Use mget for multiple files: `mget flag*.txt`

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{smb_m4nu4l_4uth}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Successfully connected to private share using credentials
- ✅ Username: `admin`
- ✅ Password: `password`
- ✅ Listed files in the private share
- ✅ Downloaded flag.txt using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes
- Incorrect username format
- Wrong password
- Not specifying share name

## Hints
1. Username: admin
2. Password: password
3. Share: private