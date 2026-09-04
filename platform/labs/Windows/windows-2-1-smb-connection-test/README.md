# Lab 2.1: SMB Connection Test

## Learning Objectives

- Connect to SMB service using smbclient
- Understand basic smbclient connection syntax
- Test anonymous SMB access
- Capture the flag (found during connection enumeration)

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

### Step 2: Verify SMB Service is Running

Before connecting, verify that SMB service (port 445) is accessible.

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

2. **Alternative quick check:**
   ```bash
   nc -zv <target_ip> 445
   ```

### Step 3: Test SMB Connection and Find Flag

Use smbclient to test the connection and enumerate the SMB service. The flag is embedded in the server information!

**Detailed Steps:**

1. **List shares and server info (this reveals the flag!):**
   ```bash
   smbclient -L //<target_ip> -N
   ```
   
   Replace `<target_ip>` with your actual target IP.

   **Command breakdown:**
   - `smbclient`: SMB client tool for accessing SMB/CIFS shares
   - `-L`: List shares on the target
   - `//<target_ip>`: Target server
   - `-N`: No password flag (anonymous access)

2. **Expected output with flag:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   public          Disk      
   IPC$            IPC       IPC Service (Windows Server - OCR{smb_c0nn3ct})
   
   Workgroup            Master
   ---------            -------
   WORKGROUP
   ```

   **The flag is in the IPC$ comment!** Look for: `OCR{smb_c0nn3ct}`

3. **Alternative: Use enum4linux:**
   ```bash
   enum4linux -a <target_ip>
   ```
   
   Look for the "Server Comment" in the output.

### Step 4: Verify Connection to Share (Optional)

You can also verify you can connect to a share:

```bash
smbclient //<target_ip>/public -N
```

**Expected output:**
```
Try "help" for a list of possible commands.
smb: \>
```

Type `exit` to disconnect.

### Step 5: Verify Flag Format

**Flag format:**
```
OCR{smb_c0nn3ct}
```

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Confirmed SMB service (port 445) is accessible
- ✅ Used `smbclient -L` to list shares and server info
- ✅ Found flag in the IPC$ service comment
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Not using `-L` flag to list shares (jumping straight to connecting)
- Not reading the IPC$ service comment
- Missing the flag in the output

## Hints for Struggling Students

1. Use `smbclient -L //<target_ip> -N` to list shares
2. The flag is in the server comment/description
3. Look at the IPC$ line - the flag is in the Comment column
4. You don't need to download any files for this lab!
