# Lab 2.8: SMB Comprehensive Null Session Enumeration

## Learning Objectives

- Perform complete enumeration via null session
- Combine multiple enumeration techniques
- Capture the flag (found during comprehensive enumeration)

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

### Step 2: Comprehensive Enumeration with enum4linux

Use enum4linux for complete null session enumeration. The flag is in the server comment!

**Detailed Steps:**

1. **Run comprehensive enumeration (reveals the flag!):**
   ```bash
   enum4linux -a <target_ip>
   ```
   
   **Key sections to look for:**
   
   **Server Information (contains flag):**
   ```
   [+] Server Information
   Server Comment: WIN-DC01 - Full Enum: OCR{smb_c0mpl3t3_null}
   ```

   **Workgroup/Domain:**
   ```
   [+] Workgroup/Domain Information
   Workgroup: FINANCECORP
   ```

   **Share Enumeration:**
   ```
   [+] Share Enumeration
   Sharename       Type      Comment
   public          Disk      Public Share
   data            Disk      Data Share
   IPC$            IPC       IPC Service
   ```

   **User Enumeration:**
   ```
   [+] User Enumeration
   user:[admin]
   user:[user1]
   user:[svc_backup]
   ```

### Step 3: Alternative - Manual Enumeration

You can also enumerate manually using individual tools:

**List shares and server info:**
```bash
smbclient -L //<target_ip> -N
```

**Expected output with flag:**
```
Sharename       Type      Comment
---------       ----      -------
public          Disk      Public Share
data            Disk      Data Share
IPC$            IPC       IPC Service (WIN-DC01 - Full Enum: OCR{smb_c0mpl3t3_null})

Workgroup            Master
---------            -------
FINANCECORP
```

**Enumerate users:**
```bash
rpcclient -U "" -N <target_ip>
rpcclient $> enumdomusers
rpcclient $> enumdomgroups
rpcclient $> exit
```

### Step 4: Document Enumeration Results

**Server Information:**
- NetBIOS Name: WIN-DC01
- Workgroup: FINANCECORP
- Server Comment: Contains the flag!

**Shares Found:**
| Share | Type | Comment |
|-------|------|---------|
| public | Disk | Public Share |
| data | Disk | Data Share |
| IPC$ | IPC | IPC Service |

**Users Found:**
| Username | Description |
|----------|-------------|
| admin | Administrator |
| user1 | Standard user |
| svc_backup | Service account |

### Step 5: Verify Flag Format

**Flag format:**
```
OCR{smb_c0mpl3t3_null}
```

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Ran comprehensive enumeration with enum4linux
- ✅ Found server information (NetBIOS name, workgroup)
- ✅ Enumerated all shares (public, data, IPC$)
- ✅ Enumerated users (admin, user1, svc_backup)
- ✅ Found flag in server comment
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using enum4linux for comprehensive enumeration
- Missing the server comment containing the flag
- Trying to access files instead of reading enumeration output

## Hints for Struggling Students

1. Use `enum4linux -a <target_ip>` for comprehensive enumeration
2. Look for the "Server Comment" in the output - it contains the flag
3. Or use `smbclient -L //<target_ip> -N` to see the flag in IPC$ comment
4. Document all findings: shares, users, workgroup, server info
