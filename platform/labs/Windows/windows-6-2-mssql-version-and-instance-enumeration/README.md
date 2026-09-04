# Lab 6.2: MS-SQL Version and Instance Enumeration
## Learning Objectives
- Enumerate MS-SQL version and instances
- Understand database enumeration
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

### Step 2: Version Detection

Use nmap with version detection to identify MS-SQL version and instances.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Run version detection scan:**
   ```bash
   nmap -sV -p 3306 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -sV -p 3306 <target_ip>`)

   **Note:** This lab uses MySQL (port 3306) as an MS-SQL alternative. Real MS-SQL runs on port 1433.

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-sV`: Version detection (probes service to determine version)
   - `-p 3306`: Scan port 3306 (MySQL default port)
   - `<target_ip>`: Target IP address

3. **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE       VERSION
   3306/tcp open  mysql         MySQL 8.0.33
   
   Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
   Nmap done: 1 IP address (1 host up) scanned in 6.45 seconds
   ```

4. **Enhanced scan with scripts:**
   ```bash
   nmap -sV -sC -p 3306 <target_ip>
   ```

5. **For real MS-SQL (port 1433):**
   ```bash
   nmap -sV -p 1433 <target_ip>
   ```

### Step 3: Analyze Version

Carefully review the version detection output to understand database information.

**Detailed Steps:**

1. **Look for version information:**
   - **Service**: `mysql` (MySQL) or `ms-sql-s` (MS-SQL)
   - **Version**: `MySQL 8.0.33` or `Microsoft SQL Server 2019`
   - **Port**: 3306 (MySQL) or 1433 (MS-SQL)

2. **Key information from output:**
   ```
   SERVICE       VERSION
   mysql         MySQL 8.0.33
   ```

3. **What this tells us:**
   - Database type: MySQL (or MS-SQL in real scenarios)
   - Version: 8.0.33 (helps identify vulnerabilities)
   - Instance information may be available
   - Helps select appropriate database client tools

4. **Additional enumeration (if MS-SQL):**
   ```bash
   nmap --script ms-sql-info -p 1433 <target_ip>
   ```

### Step 4: Access Flag

The flag is located in /tmp/flag.txt on the database server.

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
   OCR{mssql_v3rs10n}
   ```

4. **Alternative: Check if flag is accessible via database:**
   ```bash
   mysql --ssl-verify-server-cert=0 -h <target_ip> -u root -p
   # Try to access file system via database commands
   ```

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_v3rs10n}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Ran nmap version detection on database port (3306 or 1433)
- ✅ Identified database service version (MySQL 8.0.33 or MS-SQL version)
- ✅ Analyzed version information and understood database type
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Version detection reveals database software and version
- Different database types use different ports (MySQL: 3306, MS-SQL: 1433)
- Version information helps identify vulnerabilities
- Instance enumeration reveals additional database details
## Hints
1. Use nmap -sV for version
2. Check service version output
3. Flag accessible after enumeration