# Lab 7.1: LDAP Service Detection
## Learning Objectives
- Identify LDAP service on target
- Understand directory service enumeration
- Capture the flag
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

   **Expected output:**
   ```
   PING <target_ip> (<target_ip>) 56(84) bytes of data.
   64 bytes from <target_ip>: icmp_seq=1 ttl=64 time=0.123 ms
   64 bytes from <target_ip>: icmp_seq=2 ttl=64 time=0.098 ms
   64 bytes from <target_ip>: icmp_seq=3 ttl=64 time=0.105 ms
   ```

### Step 2: Scan for LDAP Service

Use nmap to scan for LDAP (Lightweight Directory Access Protocol) on its standard ports.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Scan for LDAP ports:**
   ```bash
   nmap -p 389,636 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -p 389,636 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-p 389,636`: Scan ports 389 (LDAP) and 636 (LDAPS)
   - `<target_ip>`: Target IP address

   **LDAP Ports:**
   - **Port 389**: LDAP (unencrypted)
   - **Port 636**: LDAPS (LDAP over SSL/TLS - encrypted)

3. **Expected output if LDAP is running:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT    STATE SERVICE
   389/tcp open  ldap
   636/tcp open  ldapssl
   
   Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
   ```

4. **Enhanced scan with version detection:**
   ```bash
   nmap -p 389,636 -sV <target_ip>
   ```

   **Expected output with version:**
   ```
   PORT    STATE SERVICE       VERSION
   389/tcp open  ldap          OpenLDAP 2.2.X - 2.3.X
   636/tcp open  ssl/ldap      OpenLDAP 2.2.X - 2.3.X
   ```

5. **Alternative: Scan with LDAP scripts:**
   ```bash
   nmap -p 389,636 --script ldap* <target_ip>
   ```

   This runs LDAP-specific nmap scripts for more detailed information.

### Step 3: Verify LDAP Service

Confirm that the detected service is LDAP and understand what it is.

**Detailed Steps:**

1. **What is LDAP?**
   - **LDAP** = Lightweight Directory Access Protocol
   - Port **389**: LDAP (unencrypted)
   - Port **636**: LDAPS (LDAP over SSL/TLS - encrypted)
   - Used for directory services (user accounts, groups, organizational data)
   - Common in Active Directory environments

2. **Key indicators of LDAP:**
   - Port 389 or 636 is open
   - Service names: `ldap`, `ldapssl`, `ssl/ldap`
   - Used for directory and authentication services
   - Often found in Windows Active Directory environments

3. **Verify with netcat (alternative):**
   ```bash
   nc -zv <target_ip> 389
   nc -zv <target_ip> 636
   ```

   **Expected output:**
   ```
   Connection to <target_ip> 389 port [tcp/ldap] succeeded!
   Connection to <target_ip> 636 port [tcp/ldapssl] succeeded!
   ```

4. **Test LDAP connection:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -s base
   ```

   This performs a basic anonymous LDAP bind test.

### Step 4: Access Flag File

The flag is located in `/tmp/flag.txt` on the LDAP server.

**Detailed Steps:**

1. **If you have shell access:**
   ```bash
   ssh admin@<target_ip>
   # Password: password
   ```

2. **Navigate to flag location:**
   ```bash
   cat /tmp/flag.txt
   ```

   **Expected output:**
   ```
   OCR{ldap_d3t3ct}
   ```

3. **Alternative: Check if flag is accessible via LDAP:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=*)" | grep -i flag
   ```

4. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{ldap_d3t3ct}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Scanned for LDAP ports (389, 636) using nmap
- ✅ Identified LDAP service on port 389 or 636
- ✅ Understood difference between LDAP and LDAPS
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Additional LDAP Information:**
- **LDAP (389)**: Unencrypted, faster but less secure
- **LDAPS (636)**: Encrypted, more secure but requires SSL/TLS
- Used in Active Directory for user/group management
- Can be enumerated for usernames, groups, and organizational structure
## Hints
1. LDAP on port 389
2. LDAPS on port 636
3. Use nmap to detect