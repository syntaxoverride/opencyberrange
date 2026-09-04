# Lab 2.2: SMB Share Listing

## Learning Objectives

- List SMB shares using smbclient -L
- Understand share enumeration techniques
- Identify available shares on target
- Capture the flag (found in share listing)

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

   **Expected output:**
   ```
   PORT    STATE SERVICE
   445/tcp open  microsoft-ds
   ```

### Step 2: List Available SMB Shares

Use smbclient to enumerate all available shares on the target. The flag is in one of the share comments!

**Detailed Steps:**

1. **List all available shares:**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `smbclient`: SMB client tool
   - `-L`: List shares flag (enumerates available shares)
   - `//<target_ip>`: Target server (no share name specified)
   - `-N`: No password flag (for anonymous access)

2. **Expected output with flag:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   public          Disk      Public Share
   data            Disk      Data Share
   backup          Disk      OCR{smb_sh4r3_l1st}
   IPC$            IPC       IPC Service (Windows Server)
   
   Workgroup            Master
   ---------            -------
   WORKGROUP
   ```

   **The flag is in the backup share comment!** Look for: `OCR{smb_sh4r3_l1st}`

3. **Alternative: List shares with enum4linux:**
   ```bash
   enum4linux -S <target_ip>
   ```
   
   The `-S` flag specifically enumerates shares.

### Step 3: Analyze Share Information

Review the share listing output:

| Share Name | Type | Comment |
|------------|------|---------|
| public | Disk | Public Share |
| data | Disk | Data Share |
| backup | Disk | **OCR{smb_sh4r3_l1st}** |
| IPC$ | IPC | IPC Service |

**Key observations:**
- Multiple file shares are available (public, data, backup)
- The `backup` share comment contains the flag
- IPC$ is a system share (always present)

### Step 4: Verify Flag Format

**Flag format:**
```
OCR{smb_sh4r3_l1st}
```

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Successfully listed all available shares using `smbclient -L`
- ✅ Identified the backup share with the flag in its comment
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using `-L` flag for listing shares
- Not using `-N` for anonymous access
- Not reading the Comment column in the output
- Trying to connect to a share instead of listing them

## Hints for Struggling Students

1. Use `smbclient -L //<target_ip> -N` to list shares
2. Look at the "Comment" column in the output
3. The flag is in one of the share descriptions
4. You don't need to connect to any shares - just list them!
