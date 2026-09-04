# Lab 7.3: LDAP Base DN Enumeration
## Learning Objectives
- Enumerate base DN and root DSE
- Understand LDAP structure
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before querying LDAP.

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

### Step 2: Query Root DSE

Query the Root DSE (DSA-Specific Entry) to enumerate base DN and server information.

**Detailed Steps:**

1. **Verify ldapsearch is installed:**
   ```bash
   which ldapsearch
   ```

2. **Query Root DSE:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "" -s base
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `ldapsearch -x -H ldap://<target_ip> -b "" -s base`)

   **Command breakdown:**
   - `ldapsearch`: LDAP search tool
   - `-x`: Simple authentication (anonymous bind)
   - `-H ldap://<target_ip>`: LDAP server URL
   - `-b ""`: Base DN (empty = root DSE)
   - `-s base`: Search scope (base level only)

3. **Expected output:**
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
   objectClass: OpenLDAProotDSE
   namingContexts: dc=example,dc=com
   namingContexts: dc=yourcompany,dc=local
   supportedLDAPVersion: 3
   supportedSASLMechanisms: EXTERNAL DIGEST-MD5 CRAM-MD5 LOGIN PLAIN
   ...
   
   # search result
   search: 2
   result: 0 Success
   
   # numResponses: 2
   ```

### Step 3: Find Base DN

Analyze the Root DSE output to identify the base DN.

**Detailed Steps:**

1. **Look for namingContexts in output:**
   ```
   namingContexts: dc=example,dc=com
   namingContexts: dc=yourcompany,dc=local
   ```

2. **What namingContexts means:**
   - **Base DN**: The root of the LDAP directory tree
   - **Format**: `dc=domain,dc=com` or `dc=example,dc=local`
   - **Multiple contexts**: Server may have multiple naming contexts

3. **Common base DN formats:**
   - `dc=example,dc=com` (domain example.com)
   - `dc=yourcompany,dc=local` (domain yourcompany.local)
   - `ou=Users,dc=example,dc=com` (organizational unit)

4. **Document discovered base DNs:**
   ```
   Discovered Base DNs:
   - dc=example,dc=com
   - dc=yourcompany,dc=local
   ```

5. **Test base DN:**
   ```bash
   ldapsearch -x -H ldap://<target_ip> -b "dc=example,dc=com" -s base
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
   OCR{ldap_b4s3_dn}
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
OCR{ldap_b4s3_dn}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and LDAP service accessibility
- ✅ Queried Root DSE using ldapsearch
- ✅ Identified base DN from namingContexts attribute
- ✅ Understood LDAP directory structure
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Root DSE contains server and directory information
- namingContexts reveals base DN for directory queries
- Base DN is required for most LDAP queries
- Understanding LDAP structure is essential for enumeration
- Base DN enumeration is the first step in LDAP reconnaissance
## Hints
1. Query root DSE with -b ""
2. Look for namingContexts
3. Base DN typically dc=example,dc=com