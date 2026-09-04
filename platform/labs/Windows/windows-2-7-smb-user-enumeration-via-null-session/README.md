# Lab 2.7: SMB User Enumeration via Null Session

## Learning Objectives

- Enumerate users using null session
- Understand SMB user enumeration techniques
- Capture the flag (found during user enumeration)

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

### Step 2: Enumerate Server Info with Null Session

Start by listing shares to see server information. The flag is in the server string!

**Detailed Steps:**

1. **List server info (reveals the flag!):**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   **Expected output with flag:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   IPC$            IPC       IPC Service (DC01 - Users Enumerable: OCR{smb_us3r_3num})
   
   Workgroup            Master
   ---------            -------
   WORKGROUP
   ```

   **The flag is in the IPC$ service comment!**

### Step 3: Enumerate Users Using rpcclient

Use rpcclient with null session to enumerate users on the system.

**Detailed Steps:**

1. **Connect with rpcclient:**
   ```bash
   rpcclient -U "" -N <target_ip>
   ```

2. **Enumerate domain users:**
   ```bash
   rpcclient $> enumdomusers
   ```
   
   **Expected output:**
   ```
   user:[admin] rid:[0x3e8]
   user:[user1] rid:[0x3e9]
   user:[guest] rid:[0x3ea]
   ```

3. **Get more user details:**
   ```bash
   rpcclient $> queryuser admin
   ```

4. **Exit rpcclient:**
   ```bash
   rpcclient $> exit
   ```

### Step 4: Enumerate Users Using enum4linux

Alternative method using enum4linux for comprehensive enumeration.

**Detailed Steps:**

1. **Enumerate users with enum4linux:**
   ```bash
   enum4linux -U <target_ip>
   ```
   
   The `-U` flag enumerates users.

2. **Full enumeration (also shows server info with flag):**
   ```bash
   enum4linux -a <target_ip>
   ```
   
   Look for:
   - Server Comment containing the flag
   - User list (admin, user1, guest)

### Step 5: Document Discovered Users

| Username | RID | Notes |
|----------|-----|-------|
| admin | 0x3e8 | Administrator account |
| user1 | 0x3e9 | Standard user |
| guest | 0x3ea | Guest account |

### Step 6: Verify Flag Format

**Flag format:**
```
OCR{smb_us3r_3num}
```

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Used smbclient to see server info (contains flag)
- ✅ Connected using rpcclient with null session
- ✅ Enumerated users using `enumdomusers`
- ✅ Found flag in server string
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using rpcclient for user enumeration
- Missing the flag in the server comment
- Trying to download files instead of enumerating

## Hints for Struggling Students

1. Use `smbclient -L //<target_ip> -N` to see the flag in server info
2. Use `rpcclient -U "" -N <target_ip>` for user enumeration
3. Use `enumdomusers` in rpcclient to list users
4. Or use `enum4linux -U <target_ip>` for automated user enumeration
