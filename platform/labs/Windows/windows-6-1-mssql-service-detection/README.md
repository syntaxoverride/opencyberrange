# Lab 6.1: MS-SQL Service Detection
## Learning Objectives
- Identify MS-SQL service on target
- Understand database service enumeration
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

### Step 2: Scan for MS-SQL Service

Use nmap to scan for MS-SQL (Microsoft SQL Server) on its standard port.

**Detailed Steps:**

1. **Verify nmap is installed:**
   ```bash
   which nmap
   nmap --version
   ```

2. **Scan for MS-SQL port:**
   ```bash
   nmap -p 1433 <target_ip>
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `nmap -p 1433 <target_ip>`)

   **Command breakdown:**
   - `nmap`: Network mapper tool
   - `-p 1433`: Scan port 1433 (MS-SQL default port)
   - `<target_ip>`: Target IP address

   **Note:** This lab uses MySQL (port 3306) as an MS-SQL alternative for educational purposes. In real scenarios, MS-SQL runs on port 1433.

3. **Expected output if MS-SQL is running (port 1433):**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE
   1433/tcp open  ms-sql-s
   
   Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
   ```

4. **Since this lab uses MySQL alternative, scan port 3306:**
   ```bash
   nmap -p 3306 <target_ip>
   ```

   **Expected output:**
   ```
   Starting Nmap 7.94 ( https://nmap.org ) at 2024-01-15 10:30 UTC
   Nmap scan report for <target_ip>
   Host is up (0.001s latency).
   
   PORT     STATE SERVICE
   3306/tcp open  mysql
   
   Nmap done: 1 IP address (1 host up) scanned in 0.45 seconds
   ```

5. **Enhanced scan with version detection:**
   ```bash
   nmap -p 1433,3306 -sV <target_ip>
   ```

   **Expected output:**
   ```
   PORT     STATE SERVICE       VERSION
   1433/tcp closed ms-sql-s
   3306/tcp open  mysql         MySQL 8.0.33
   ```

### Step 3: Verify Database Service

Confirm that the detected service is a database service and understand the difference between MS-SQL and MySQL.

**Detailed Steps:**

1. **What is MS-SQL?**
   - **MS-SQL** = Microsoft SQL Server
   - Port **1433**: Standard MS-SQL port
   - Microsoft's relational database management system
   - Used for enterprise database applications

2. **What is MySQL?**
   - **MySQL** = Open-source relational database
   - Port **3306**: Standard MySQL port
   - Used as alternative in this lab for educational purposes
   - Similar functionality to MS-SQL

3. **Key indicators:**
   - Port 1433: MS-SQL Server
   - Port 3306: MySQL Server
   - Service names: `ms-sql-s`, `mysql`
   - Database services for storing and managing data

4. **Verify with netcat (alternative):**
   ```bash
   nc -zv <target_ip> 1433
   nc -zv <target_ip> 3306
   ```

### Step 4: Connect to Database Service

Connect to the database service to verify access and locate the flag.

**Detailed Steps:**

1. **For MySQL (this lab):**
   ```bash
   mysql --ssl-verify-server-cert=0 -h <target_ip> -u root -p
   ```
   
   When prompted for password, try: `password` or press Enter for no password.

2. **Expected MySQL connection:**
   ```
   Enter password:
   Welcome to the MySQL monitor.  Commands end with ; or \g.
   ...
   mysql>
   ```

3. **For MS-SQL (real scenarios):**
   ```bash
   mssqlclient.py admin:password@<target_ip>
   ```
   
   Or using sqlcmd:
   ```bash
   sqlcmd -S <target_ip> -U admin -P password
   ```

4. **List databases:**
   ```sql
   SHOW DATABASES;
   ```

5. **Exit database client:**
   ```sql
   exit
   ```
   
   Or press `Ctrl+D`

### Step 5: Access Flag File

The flag is located in `/tmp/flag.txt` on the database server (accessible after connection).

**Detailed Steps:**

1. **If you have shell access via database:**
   - Some database configurations allow file system access
   - Flag may be accessible through database commands

2. **Alternative: Access via SSH (if available):**
   ```bash
   ssh admin@<target_ip>
   # Password: password
   ```

3. **Navigate to flag location:**
   ```bash
   cat /tmp/flag.txt
   ```

   **Expected output:**
   ```
   OCR{mssql_d3t3ct}
   ```

4. **Alternative: Check if flag is in database:**
   ```sql
   SELECT * FROM information_schema.tables;
   SELECT * FROM flag_table;
   ```

### Step 6: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_d3t3ct}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and network connectivity
- ✅ Scanned for MS-SQL port (1433) using nmap
- ✅ Identified database service (MySQL on 3306 as alternative)
- ✅ Understood difference between MS-SQL and MySQL
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`
## Hints
1. MS-SQL typically on port 1433
2. The lab service is MySQL on port 3306
3. Use nmap to detect