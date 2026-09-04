# Lab 1.5: Comprehensive Windows Enumeration

## Learning Objectives

- Perform comprehensive enumeration combining port scan, version detection, and OS detection
- Identify all Windows services (SMB, RDP, LDAP)
- Apply complete enumeration workflow
- Capture the flag (found during SMB enumeration)

## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before scanning.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

### Step 2: Perform Comprehensive Port Scan

Run nmap with all enumeration options to perform a complete reconnaissance of the target.

**Detailed Steps:**

1. **Run comprehensive nmap scan:**
   ```bash
   sudo nmap -sV -O -p- <target_ip>
   ```
   
   **Command breakdown:**
   - `sudo`: Required for OS detection
   - `-sV`: Version detection
   - `-O`: OS detection
   - `-p-`: Scan all ports (1-65535)

2. **Or scan common Windows ports (faster):**
   ```bash
   sudo nmap -sV -O -p 139,389,445,3389 <target_ip>
   ```

3. **Expected output:**
   ```
   PORT     STATE SERVICE       VERSION
   139/tcp  open  netbios-ssn   Samba smbd 4.x
   389/tcp  open  ldap          OpenLDAP
   445/tcp  open  microsoft-ds  Samba smbd 4.x
   3389/tcp open  ms-wbt-server Microsoft Terminal Services
   ```

### Step 3: Identify All Services

Document all discovered services:

| Port | Service | Description |
|------|---------|-------------|
| 139  | NetBIOS-SSN | NetBIOS Session Service |
| 389  | LDAP | Lightweight Directory Access Protocol |
| 445  | SMB | Server Message Block (file sharing) |
| 3389 | RDP | Remote Desktop Protocol |

### Step 4: Enumerate SMB to Find the Flag

The flag is embedded in the SMB server string. Use SMB enumeration to discover it!

**Detailed Steps:**

1. **Enumerate SMB shares and server info:**
   ```bash
   smbclient -L //<target_ip> -N
   ```

2. **Expected output with flag:**
   ```
   Sharename       Type      Comment
   ---------       ----      -------
   IPC$            IPC       IPC Service (Windows Server 2019 DC - Comprehensive Enum Complete: OCR{c0mpr3h3ns1v3_3num})
   ```

3. **Alternative: Use enum4linux:**
   ```bash
   enum4linux -a <target_ip>
   ```
   
   Look for the server comment in the output.

4. **Alternative: Use rpcclient:**
   ```bash
   rpcclient -U "" -N <target_ip> -c "srvinfo"
   ```

### Step 5: Verify Flag Format

**Flag format:**
```
OCR{c0mpr3h3ns1v3_3num}
```

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Performed comprehensive scan with `sudo nmap -sV -O`
- ✅ Identified all services: SMB (139/445), LDAP (389), RDP (3389)
- ✅ Enumerated SMB using `smbclient -L` or enum4linux
- ✅ Found flag in the SMB server string
- ✅ Verified flag format is correct: `OCR{...}`

## Common Mistakes

- Only running nmap without following up with service-specific enumeration
- Not using `smbclient -L` to enumerate SMB details
- Missing the flag in the server comment/description

## Hints for Struggling Students

1. Use `sudo nmap -sV -O` for comprehensive scanning
2. After finding SMB (445), enumerate it with `smbclient -L //<ip> -N`
3. The flag is in the SMB server string - look at the IPC$ share comment
4. Use `enum4linux -a <ip>` for detailed Windows enumeration
