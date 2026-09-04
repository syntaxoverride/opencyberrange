# Lab 6.3: MS-SQL Manual Authentication
## Learning Objectives
- Connect to MS-SQL with known credentials
- Understand database authentication
- Capture the flag
## Solution Walkthrough

### Step 1: Obtain Target IP Address

Get the target IP address from the lab platform before connecting.

**Detailed Steps:**

1. **Discover the target IP:**
   - The lab panel shows your network subnet (e.g., `10.X.Y.0/24`)
   - Scan the subnet to find live hosts: `nmap -sn <subnet>`
   - The target will be one of the discovered hosts

2. **Verify network connectivity:**
   ```bash
   ping -c 3 <target_ip>
   ```

3. **Verify MySQL service is running:**
   ```bash
   nmap -p 3306 <target_ip>
   ```

### Step 2: Connect

Connect to the MySQL database using provided credentials.

**Detailed Steps:**

1. **Verify MySQL client is installed:**
   ```bash
   which mysql
   ```

2. **Connect to MySQL database:**
   ```bash
   mysql --ssl-verify-server-cert=0 -h <target_ip> -u sa -p
   ```
   
   Replace `<target_ip>` with your actual target IP (e.g., `mysql --ssl-verify-server-cert=0 -h <target_ip> -u sa -p`)

   **Command breakdown:**
   - `mysql`: MySQL client tool
   - `-h <target_ip>`: Target host IP address
   - `-u sa`: Username (sa = system administrator)
   - `-p`: Prompt for password

3. **Enter password when prompted:**
   ```
   Enter password:
   ```
   
   Type: `password` (password will not be visible as you type)

4. **Expected successful connection:**
   ```
   Welcome to the MySQL monitor.  Commands end with ; or \g.
   Your MySQL connection id is 123
   Server version: 8.0.33 MySQL Community Server
   
   mysql>
   ```

   **What this means:**
   - Authentication was successful
   - You're now connected to the MySQL database
   - `mysql>` is the MySQL prompt

**Troubleshooting:**
- **"Access denied"**: Check username (sa) and password (password)
- **"Can't connect"**: Verify IP and port 3306
- **"Unknown host"**: Check network connectivity

### Step 3: Verify Connection

Confirm the connection is working by executing a test query.

**Detailed Steps:**

1. **Check MySQL version:**
   ```sql
   SELECT VERSION();
   ```

   **Expected output:**
   ```
   +-----------+
   | VERSION() |
   +-----------+
   | 8.0.33    |
   +-----------+
   1 row in set (0.00 sec)
   ```

2. **List databases:**
   ```sql
   SHOW DATABASES;
   ```

3. **Select current database:**
   ```sql
   SELECT DATABASE();
   ```

4. **Exit MySQL client:**
   ```sql
   exit
   ```
   
   Or press `Ctrl+D`

### Step 4: Access Flag

The flag is located in /tmp/flag.txt on the database server (accessible via file system).

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
   OCR{mssql_m4nu4l_4uth}
   ```

4. **Alternative: Check if flag is in database:**
   ```sql
  ; If still connected to MySQL
   SELECT * FROM information_schema.tables;
  ; Look for flag table
   ```

5. **Verify file exists:**
   ```bash
   ls -la /tmp/flag.txt
   ```

### Step 5: Verify Flag Format

Ensure the flag is in the correct format before submission.

**Flag format:**
```
OCR{mssql_m4nu4l_4uth}
```

**Verification checklist:**
- ✅ Starts with `OCR{`
- ✅ Ends with `}`
- ✅ Contains only alphanumeric characters and underscores
- ✅ No extra spaces or characters

**Success Criteria:**
- ✅ Verified target IP and MySQL service accessibility
- ✅ Successfully connected to MySQL database using mysql client
- ✅ Logged in with credentials (sa/password)
- ✅ Verified connection by executing SELECT VERSION()
- ✅ Successfully accessed flag in /tmp/flag.txt
- ✅ Verified flag format is correct: `OCR{...}`

**Key Learning Points:**
- Database authentication requires username and password
- sa (system administrator) is a common database admin account
- Understanding database connection process is essential
- Manual authentication verifies credentials work
- File system access may be separate from database access
## Hints
1. Username: sa
2. Password: password
3. Use mysql client
4. Flag in /tmp/flag.txt